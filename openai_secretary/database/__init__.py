from openai_secretary.database.connection import db
from openai_secretary.database.models import Master, Conversation, Message

db.generate_mapping(create_tables=True)

__all__ = [
  'Master',
  'Conversation',
  'Message',
]
