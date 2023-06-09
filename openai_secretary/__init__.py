from os.path import dirname, join
from typing import Optional
from openai_secretary.agent import Agent
from openai_secretary.database.models import Conversation, Message
from openai_secretary.resource import ContextItem, Emotion, IAgent


def init_agent(*, debug: bool = False, conversation_id: Optional[int] = None) -> Agent:
  with open(join(dirname(__file__), '..', '.secret')) as f:
    key = f.read().strip()

  agent = Agent(key, debug=debug, conversation_id=conversation_id)

  return agent
