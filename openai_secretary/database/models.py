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


class SavedEmotion(db.Entity):
  id = orm.PrimaryKey(int, auto=True, size=64)
  emotion_set = orm.Required(str)


class Intimacy(db.Entity):
  id = orm.PrimaryKey(int, auto=True)
  channel_id = orm.Required(int, size=64)
  user_id = orm.Required(int, size=64)
  value = orm.Required(float)

  @classmethod
  @orm.db_session
  def get_value(cls, channel_id: int, user_id: int) -> float:
    intimacy = cls.get(channel_id=channel_id, user_id=user_id)
    if intimacy is None:
      return 0
    return intimacy.value

  @classmethod
  @orm.db_session
  def set_value(cls, channel_id: int, user_id: int, value: float) -> None:
    intimacy = cls.get(channel_id=channel_id, user_id=user_id)
    if intimacy is None:
      cls(channel_id=channel_id, user_id=user_id, value=value)
    else:
      intimacy.value = value

  @classmethod
  @orm.db_session
  def add_value(cls, channel_id: int, user_id: int, value: float) -> None:
    intimacy = cls.get(channel_id=channel_id, user_id=user_id)
    if intimacy is None:
      cls(channel_id=channel_id, user_id=user_id, value=value)
    else:
      intimacy.value += value


class Message(db.Entity):
  id = orm.PrimaryKey(int, auto=True, size=64)
  index = orm.Required(int)
  role = orm.Required(str)
  text = orm.Required(str)
  embeddings = orm.Optional(str, nullable=True)
  created_at = orm.Required(datetime)
  conversation = orm.Required(Conversation)


class Settings(db.Entity):
  id = orm.PrimaryKey(int, auto=True, size=64)
  settings = orm.Required(str)
