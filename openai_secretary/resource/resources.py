from datetime import datetime
from typing import Literal, Required, TypedDict

from openai_secretary.database.models import Conversation

RoleType = Literal['system', 'assistant', 'user']


class ContextItem(TypedDict):
  role: Required[RoleType]
  content: Required[str]


initial_messages: list[tuple[RoleType, str]] = [
  ('system', 'とある企業の社長を補佐する従順な秘書になりきって応答してください。口調は礼儀正しく、丁寧なものにしてください。'),
]


def create_initial_context(conv: Conversation | None) -> list[ContextItem]:
  context = []
  context.append({'role': 'system', 'content': f'起動時刻は{datetime.now().strftime("%Y年%m月%d日 %H時%M分%S秒")}です'})
  if conv is not None:
    context.append({'role': 'system', 'content': f'前回終了時刻は{conv.last_interact_at.strftime("%Y年%m月%d日 %H時%M分%S秒")}です。'})
  else:
    context.append({'role': 'system', 'content': '前回終了時刻は記録されていません。今回が初めての起動です。'})

  return context
