from datetime import datetime
import json
import logging
from typing import Any

import openai as oai
from openai.openai_object import OpenAIObject
from openai.error import Timeout
from pony.orm import db_session, desc, select, raw_sql

from openai_secretary.database import Master
from openai_secretary.database.models import Conversation, Message, SavedEmotion
from openai_secretary.resource import ContextItem, Emotion, IAgent
import openai_secretary.resource.resources as res

logger = logging.getLogger('oai_chatbot.agent')


class Agent(IAgent):
  context: list[ContextItem]
  emotion: Emotion
  emotion_delta: float = 0.5
  cid: int

  @property
  def _debug(self) -> bool:
    return logger.level <= logging.DEBUG

  @_debug.setter
  def _debug(self, value: bool) -> None:
    logger.setLevel(logging.DEBUG if value else logging.INFO)

  @db_session
  def __init__(self, api_key: str | None, *, debug: bool = False, conversation_id: int | None = None):
    self._debug = debug
    logger.debug('debug logs on.')

    master: Master | None = Master.select().order_by(desc(Master.version)).first()

    if master is None or master.api_key != api_key:
      master = Master(api_key=api_key)

    oai.api_key = master.api_key

    if conversation_id is not None:
      conv = Conversation.get(id=conversation_id)
    else:
      conv = Conversation.select().order_by(desc(Conversation.last_interact_at)).first()

    if conv is None:
      logger.debug('no existing conversations found. initializing conversation.')
      conv = self.init_conversation(conversation_id)

    system = select(m for m in Message if m.role == 'system' and m.conversation == conv).order_by(Message.index)
    self.cid = conv.id

    emo = SavedEmotion.get(id=self.cid)
    if emo is None:
      self.emotion = Emotion.random_emotion()
      SavedEmotion(id=self.cid, emotion_set=json.dumps(self.emotion.json()))
    else:
      self.emotion = Emotion(*json.loads(emo.emotion_set))

    self.context = [{'role': msg.role, 'content': msg.text} for msg in system]
    res.create_initial_context(conv, self)

  def debugLog(self, *args: Any) -> None:
    if self._debug:
      print('[DEBUG]', *args)

  @property
  @db_session
  def initial_message(self) -> str:
    # yapf: disable
    return select(
      m for m in Message
      if m.role == 'system' and m.conversation.id == self.cid
    ).order_by(
      Message.index,
    ).first().text
    # yapf: enable

  @initial_message.setter
  @db_session
  def initial_message(self, message: str) -> None:
    # yapf: disable
    msg = select(
      m for m in Message if m.role == 'system' and m.conversation.id == self.cid
    ).order_by(Message.index).first()
    msg.text = message
    self.context[0]['content'] = message
    # yapf: enable

  @db_session
  def init_conversation(self, id: int | None) -> Conversation:
    if id is None:
      conv = Conversation(
        name='Default',
        description='Default conversation',
        created_at=datetime.now(),
        last_interact_at=datetime.now(),
      )
    else:
      conv = Conversation(
        id=id,
        name=f'conversation@{id}',
        description='Default conversation',
        created_at=datetime.now(),
        last_interact_at=datetime.now(),
      )

    for i, (role, text) in enumerate(res.initial_messages):
      Message(
        index=i,
        role=role,
        text=text,
        created_at=datetime.now(),
        embeddings=None,
        conversation=conv,
      )

    return conv

  async def get_embedding_vector(self, text: str) -> list[str]:
    resp: OpenAIObject = await oai.Embedding.acreate(model="text-search-ada-doc-001", input=text)
    obj = resp.get('data', [{}])[0]
    assert obj['object'] == 'embedding'
    return obj['embedding']

  async def get_emotional_vector(self, text: str) -> list[float]:
    prompt = f"""evaluate how the text moves emotions along each of the five axes with a number within 20 steps -10 to 10.
evaluation must be in the format: `[<anger>, <disgust>, <fear>, <joy>, <sadness>]`.
extreme evaluations are not preferable.

text:{text}
evaluation:"""
    try:
      resp: OpenAIObject = await oai.Completion.acreate(
        model="text-davinci-003",
        prompt=prompt,
        temperature=0.2,
        max_tokens=64,
        top_p=1,
        best_of=3,
        frequency_penalty=0,
        presence_penalty=0,
        request_timeout=10.0,
        timeout=5.0,
      )
      vec: list[int] = json.loads(resp["choices"][0]["text"].strip().split('\n')[0])
    except:
      return [0.0, 0.0, 0.0, 0.0, 0.0]

    return [i / 10 * self.emotion_delta for i in vec]

  def create_context_for_reply(self, c: Conversation, search_vec: str) -> list[ContextItem]:
    context = self.context.copy()
    recent = [
      *select(m for m in Message if m.role != 'system' and m.conversation == c).order_by(desc(Message.index))[:10]
    ]
    recent.reverse()
    context.extend({'role': msg.role, 'content': msg.text} for msg in recent)
    oldest_recent_index = recent[0].index if recent else 0

    # yapf: disable
    ctx = select(
      (m, raw_sql('similarity(m.embeddings, $search_vec) as "sim"', result_type=float))
      for m in Message if m.embeddings is not None and m.index < oldest_recent_index and m.conversation == c
    ).order_by(
      lambda m, s: desc(raw_sql('"sim"'))
    )[:10]
    # yapf: enable

    for m, similarity in ctx:
      context.append({'role': 'system', 'content': f'過去にこんな会話をした:{m.text}'})
      logger.debug(f'related message (similarity: {similarity}): {m.text}')

    return context

  async def update_emotion(self, message: str) -> None:
    em = await self.get_emotional_vector(message)
    logger.debug(f'emotion delta: {em}')
    self.emotion += em
    logger.debug(f'current emotion: {repr(self.emotion)}')

  async def talk(self, message: str, injected_system_message: str | None = None, need_response: bool = True) -> str:
    with db_session:
      c = Conversation.get(id=self.cid)

      vec1 = await self.get_embedding_vector(message)
      context = self.create_context_for_reply(c, str(vec1))
      await self.update_emotion(message)

      s_emo = SavedEmotion.get(id=self.cid)
      s_emo.emotion_set = json.dumps(self.emotion.json())

      context.append({'role': 'system', 'content': f'あなたの今の心情は{self.emotion}である。'})

      if injected_system_message is not None:
        context.append({'role': 'system', 'content': injected_system_message})

      context.append({'role': 'user', 'content': message})

      msg = Message(
        index=len(c.messages),
        role='user',
        text=message,
        embeddings=str(vec1),
        created_at=datetime.now(),
        conversation=c,
      )

      if not need_response:
        logger.debug('no response needed')
        return ''

      logger.debug(json.dumps(context, indent=2, ensure_ascii=False))

      while True:
        try:
          response = await oai.ChatCompletion.acreate(
            model='gpt-3.5-turbo',
            messages=context,
            temperature=0.8,
            max_tokens=256,
            request_timeout=(3.0, 20.0),
            timeout=10.0,
          )
          break
        except Timeout as e:
          logger.warn(f'read error: {type(e)}: {e}')
          pass
        except Exception as e:
          logger.error(f'read error: {type(e)}: {e}')
          raise

      text = response["choices"][0]["message"]["content"]

      logger.debug(f'tokens consumed: {response["usage"]["total_tokens"]}')

      vec2 = await self.get_embedding_vector(text)

      msg = Message(
        index=len(c.messages),
        role='assistant',
        text=text,
        embeddings=str(vec2),
        created_at=datetime.now(),
        conversation=c
      )

      c.last_interact_at = datetime.now()
      return msg.text
