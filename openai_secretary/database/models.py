from datetime import datetime
from pony import orm
from openai_secretary.database import db


class Master(db.Entity):
  version = orm.PrimaryKey(int, auto=True, size=64)
  api_key = orm.Required(str)


class Conversation(db.Entity):
  id = orm.PrimaryKey(int, auto=True, size=64)
  name = orm.Optional(str)
  description = orm.Optional(str)
  messages = orm.Set(lambda: Message)
  created_at = orm.Required(datetime)
  last_interact_at = orm.Required(datetime)


class Message(db.Entity):
  id = orm.PrimaryKey(int, auto=True, size=64)
  index = orm.Required(int)
  role = orm.Required(str)
  text = orm.Required(str)
  embeddings = orm.Optional(str, nullable=True)
  created_at = orm.Required(datetime)
  conversation = orm.Required(Conversation)
