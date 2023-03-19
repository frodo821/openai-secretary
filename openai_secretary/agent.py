from datetime import datetime
import json
from typing import Any, Optional

import openai as oai
from openai.openai_object import OpenAIObject
from pony.orm import db_session, desc, select, raw_sql

from openai_secretary.database import Master
from openai_secretary.database.models import Conversation, Message
from openai_secretary.resource import ContextItem, Emotion, IAgent
import openai_secretary.resource.resources as res


class Agent(IAgent):
  context: list[ContextItem]
  emotion: Emotion
  emotion_delta: float = 0.5
  cid: int
  _debug: bool

  @db_session
  def __init__(self, api_key: Optional[str], *, debug: bool = False, conversation_id: Optional[int] = None):
    self._debug = debug
    self.debugLog('debug logs on.')

    master: Master | None = Master.select().order_by(desc(Master.version)).first()

    if master is None or master.api_key != api_key:
      master = Master(api_key=api_key)

    oai.api_key = master.api_key

    if conversation_id is not None:
      conv = Conversation.get(id=conversation_id)
    else:
      conv = Conversation.select().order_by(desc(Conversation.last_interact_at)).first()

    if conv is None:
      self.debugLog('no existing conversations found. initializing conversation.')
      conv = self.init_conversation(conversation_id)

    system = select(m for m in Message if m.role == 'system' and m.conversation == conv).order_by(Message.index)
    self.cid = conv.id

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
  def init_conversation(self, id: Optional[int]) -> Conversation:
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

  def get_embedding_vector(self, text: str) -> list[str]:
    resp: OpenAIObject = oai.Embedding.create(model="text-embedding-ada-002", input=text)
    obj = resp.get('data', [{}])[0]
    assert obj['object'] == 'embedding'
    return obj['embedding']

  def get_emotional_vector(self, text: str) -> list[float]:
    prompt = f"""evaluate how the text moves emotions along each of the five axes with a number within 20 steps -10 to 10.
evaluation must be in the format: `[<anger>, <disgust>, <fear>, <joy>, <sadness>]`.
extreme evaluations are not preferable.

text:{text}
evaluation:"""
    resp: OpenAIObject = oai.Completion.create(
      model="text-davinci-003",
      prompt=prompt,
      temperature=0.2,
      max_tokens=64,
      top_p=1,
      best_of=3,
      frequency_penalty=0,
      presence_penalty=0,
    )
    vec: list[int] = json.loads(resp["choices"][0]["text"].strip().split('\n')[0])

    return [i / 10 * self.emotion_delta for i in vec]

  @db_session
  def talk(self, message: str, need_response: bool = True) -> str:
    c = Conversation.get(id=self.cid)

    vec1 = self.get_embedding_vector(message)

    context = self.context.copy()
    recent = [*select(m for m in Message if m.role != 'system' and m.conversation == c).order_by(desc(Message.index))[:20]]
    recent.reverse()
    context.extend({'role': msg.role, 'content': msg.text} for msg in recent)

    search_vec = str(vec1)
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
      context.append({'role': 'system', 'content': f'関連する会話ログ(発言者: {m.role}): {m.text}'})
      self.debugLog(f'related message (similarity: {similarity}): {m.text}')

    em = self.get_emotional_vector(message)
    self.debugLog('emotion delta:', em)
    self.emotion.anger += em[0]
    self.emotion.disgust += em[1]
    self.emotion.fear += em[2]
    self.emotion.joy += em[3]
    self.emotion.sadness += em[4]
    self.debugLog('current emotion:', repr(self.emotion))

    context.append({
      'role': 'system',
      'content': f'シミュレートされたあなたの今の感情は次の通りです。\n{self.emotion}\nこの感情に従って、会話を続けてください。',
    })

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
      return ''

    while True:
      try:
        response = oai.ChatCompletion.create(
          model='gpt-3.5-turbo',
          messages=context,
          request_timeout=(3.0, 20.0),
        )
        break
      except Exception as e:
        self.debugLog('read error:', e)
        pass

    text = response["choices"][0]["message"]["content"]

    vec2 = self.get_embedding_vector(text)

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
