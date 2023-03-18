from datetime import datetime
import json
from typing import Optional

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

  @db_session
  def __init__(self, api_key: Optional[str]):
    master: Master | None = Master.select().order_by(desc(Master.version)).first()

    if master is None or master.api_key != api_key:
      master = Master(api_key=api_key)

    oai.api_key = master.api_key

    conv = select(c for c in Conversation).order_by(desc(Conversation.last_interact_at)).first()

    if conv is None:
      conv = self.init_conversation()

    system = select(m for m in Message if m.role == 'system').order_by(Message.index)

    self.context = [{'role': msg.role, 'content': msg.text} for msg in system]
    res.create_initial_context(conv, self)

  @db_session
  def init_conversation(self) -> Conversation:
    conv = Conversation(
      name='Default',
      description='Default conversation',
      created_at=datetime.now(),
      last_interact_at=datetime.now(),
    )

    for i, (role, text) in enumerate(res.initial_messages):
      msg = Message(
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
  def talk(self, message: str) -> str:
    conv = select(c for c in Conversation).order_by(desc(Conversation.last_interact_at)).first()

    vec1 = self.get_embedding_vector(message)

    context = self.context.copy()
    recent = [*select(m for m in Message).order_by(Message.index)[:20]]
    context.extend({'role': msg.role, 'content': msg.text} for msg in recent)

    search_vec = str(vec1)
    oldest_recent_index = recent[0].index

    # yapf: disable
    ctx = select(
      m for m in Message if m.embeddings is not None and m.index < oldest_recent_index
    ).order_by(
      lambda m: desc(raw_sql("similarity(m.embeddings, $search_vec)"))
    )[:10]
    # yapf: enable

    for m in ctx:
      context.append({'role': 'system', 'content': f'関連する会話ログ(発言者: {m.role}): {m.text}'})

    em = self.get_emotional_vector(message)
    self.debugLog('emotion delta:', em)
    self.emotion.anger += em[0]
    self.emotion.disgust += em[1]
    self.emotion.fear += em[2]
    self.emotion.joy += em[3]
    self.emotion.sadness += em[4]

    context.append({
      'role': 'system',
      'content': f'シミュレートされたあなたの今の感情は次の通りです。\n{self.emotion}\nこの感情に従って、会話を続けてください。',
    })

    context.append({'role': 'user', 'content': message})

    msg = Message(
      index=len(conv.messages),
      role='user',
      text=message,
      embeddings=str(vec1),
      created_at=datetime.now(),
      conversation=conv,
    )

    response = oai.ChatCompletion.create(
      model='gpt-3.5-turbo',
      messages=context,
    )

    text = response["choices"][0]["message"]["content"]

    vec2 = self.get_embedding_vector(text)

    msg = Message(
      index=len(conv.messages),
      role='assistant',
      text=text,
      embeddings=str(vec2),
      created_at=datetime.now(),
      conversation=conv
    )

    conv.last_interact_at = datetime.now()
    return msg.text
