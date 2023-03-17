from datetime import datetime
from typing import Optional, Required, TypedDict

import openai as oai
from openai.openai_object import OpenAIObject
from pony.orm import db_session, desc, select, raw_sql

from openai_secretary.database import Master
from openai_secretary.database.models import Conversation, Message
from openai_secretary.resource import ContextItem, Emotion, IAgent, create_initial_context, initial_messages


class Agent(IAgent):
  context: list[ContextItem]
  emotion: Emotion

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
    create_initial_context(conv, self)

  @db_session
  def init_conversation(self) -> Conversation:
    conv = Conversation(
      name='Default',
      description='Default conversation',
      created_at=datetime.now(),
      last_interact_at=datetime.now(),
    )

    for i, (role, text) in enumerate(initial_messages):
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
      print('[DEBUG]', m.role, m.text)
      context.append({'role': 'system', 'content': f'関連する会話ログ(発言者: {m.role}): {m.text}'})
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
