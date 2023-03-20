import asyncio
from json import dumps, loads
from logging import getLogger
from random import random
from typing import Any, Required, TypedDict
from discord.flags import Intents
from discord.client import Client
from discord.message import Message
from openai_secretary import Agent, init_agent
from pony.orm import db_session
from openai_secretary.database.models import Settings, Intimacy
from openai_secretary.resource.emotion import EmotionDelta
from openai_secretary.resource.resources import compute_intimacy_delta, intimacy_prompt


class SettingsDict(TypedDict):
  response_ratio: Required[float]
  cmd_prefix: Required[str]
  _debug: Required[bool]


def registerHandlers(impl: Any, client: Client) -> None:
  for attr in (attr for attr in dir(impl) if attr.startswith('on_')):
    client.event(getattr(impl, attr))


logger = getLogger('discord.bot')


class OpenAIChatBot:
  client: Client
  __secret: str
  default_response_ratio: float
  default_cmd_prefix: str = '!'

  settings: dict[int, SettingsDict]
  agents: dict[int, Agent]
  latest_message_id: dict[int, bool]
  emotion_delta: dict[int, dict[int, EmotionDelta]]
  task: asyncio.Task[None]

  def __init__(self, secret: str, *, response_ratio=0.2) -> None:
    intents = Intents.default()
    intents.message_content = True

    self.client = Client(intents=intents)
    self.__secret = secret
    self.default_response_ratio = response_ratio
    self.agents = {}
    self.settings = {}
    self.latest_message_id = {}
    self.emotion_delta = {}
    registerHandlers(self, self.client)

  def prefix(self, channel_id: int) -> str:
    return self.settings[channel_id]['cmd_prefix']

  def response_ratio(self, channel_id: int) -> float:
    return self.settings[channel_id]['response_ratio']

  def init_settings(self, channel_id: int) -> None:
    with db_session:
      settings = Settings.get(id=channel_id)
      if settings:
        self.settings[channel_id] = loads(settings.settings)
      else:
        self.settings[channel_id] = {
          'cmd_prefix': self.default_cmd_prefix,
          'response_ratio': self.default_response_ratio,
          '_debug': True,
        }
        Settings(id=channel_id, settings=dumps(self.settings[channel_id]))

  def update_settings(self, channel_id: int) -> None:
    with db_session:
      settings = Settings.get(id=channel_id)
      settings.settings = dumps(self.settings[channel_id])

  def start(self) -> None:
    self.client.run(self.__secret)

  async def on_ready(self) -> None:
    self.task = asyncio.get_event_loop().create_task(self.update_intimacy())
    logger.info(f'Logged in as {self.client.user}')
    await self.task

  async def update_intimacy(self) -> None:
    logger.info('intimacy updater has been started.')
    while True:
      # update intimacy every 15 minutes
      await asyncio.sleep(15*60)
      logger.info('updating intimacy...')
      for cid, deltas in self.emotion_delta.items():
        for uid, delta in deltas.items():
          value = compute_intimacy_delta(delta)
          Intimacy.add_value(channel_id=cid, user_id=uid, value=value)
          logger.info(f'intimacy for user {uid} in channel {cid} is updated by {value}.')
        deltas.clear()

  async def cmd_response_ratio(self, message: Message, args: str) -> None:
    cid = message.channel.id
    if not args:
      await message.channel.send(f'`[SYSTEM]` 現在の返答率は{self.response_ratio(cid)}です。')
      return

    self.settings[cid]['response_ratio'] = float(args)
    self.update_settings(cid)
    await message.channel.send(f'`[SYSTEM]` 返答率を{self.response_ratio(cid)}に更新しました。')

  async def cmd_initial_prompt(self, message: Message, args: str) -> None:
    if not args:
      await message.channel.send(
        f'`[SYSTEM]` 現在の初期プロンプトは「{self.agents[message.channel.id].initial_message}」です。',
      )
      return

    self.agents[message.channel.id].initial_message = args
    await message.channel.send(f'`[SYSTEM]` 初期プロンプトを「{self.agents[message.channel.id].initial_message}」に更新しました。')

  async def cmd_prefix(self, message: Message, args: str) -> None:
    cid = message.channel.id

    if not args:
      await message.channel.send(f'`[SYSTEM]` 現在のコマンドプレフィックスは `{self.prefix(cid)}` です。')
      return

    self.settings[cid] = args.strip()
    self.update_settings(cid)
    await message.channel.send(f'`[SYSTEM]` コマンドプレフィックスを `{self.prefix(cid)}` に更新しました。')

  async def cmd_debug(self, message: Message, args: str) -> None:
    cid = message.channel.id
    if not args:
      await message.channel.send(
        f"[SYSTEM] `{self.prefix(cid)}debug` 使用法:\n"
        f"・`{self.prefix(cid)}debug console (on | off)` - コンソールデバッグを有効または無効にします。\n"
        f"・`{self.prefix(cid)}debug emotion` - 現在の感情値を表示します。\n",
        f"・`{self.prefix(cid)}debug intimacy [@user]` - 現在の親密度を表示します。\n",
      )
      return

    match args.split():
      case ['console', 'on']:
        self.settings[cid]['_debug'] = self.agents[cid]._debug = True
        self.update_settings(cid)
        await message.channel.send(f'`[SYSTEM]` コンソールデバッグを有効に切り替えました。')
      case ['console', 'off']:
        self.settings[cid]['_debug'] = self.agents[cid]._debug = False
        self.update_settings(cid)
        await message.channel.send(f'`[SYSTEM]` コンソールデバッグを無効に切り替えました。')
      case ['console']:
        await message.channel.send(
          f'`[SYSTEM]` 現在のデバッグモードは{"有効" if self.agents[cid]._debug else "無効"}です。',
        )
      case ['emotion']:
        await message.channel.send(f'`[SYSTEM]` 現在の感情は{repr(self.agents[cid].emotion)}です。')
      case ['intimacy']:
        value = Intimacy.get_value(channel_id=cid, user_id=message.author.id)
        prompt = intimacy_prompt(value, message.author.display_name)
        prompt = prompt[4:-4] if prompt else '中立'
        await message.channel.send(f'`[SYSTEM]` 現在のあなたに対する親密度は{value}です。({prompt})')
      case ['intimacy', 'set', value, *_]:
        value = float(value)
        if not message.mentions:
          Intimacy.set_value(channel_id=cid, user_id=message.author.id, value=value)
          prompt = intimacy_prompt(value, message.author.display_name)
          prompt = prompt[4:-4] if prompt else '中立'
          await message.channel.send(f'`[SYSTEM]` あなたに対する親密度を{value}({prompt})に更新しました。')
        else:
          for mention in message.mentions:
            Intimacy.set_value(channel_id=cid, user_id=mention.id, value=value)
            prompt = intimacy_prompt(value, mention.display_name)
            prompt = prompt[4:-4] if prompt else '中立'
            await message.channel.send(f'`[SYSTEM]` <@!{mention.id}> に対する親密度を{value}({prompt})に更新しました。')
      case ['intimacy', _]:
        if not message.mentions:
          await message.channel.send(f'`[SYSTEM]` ユーザーを指定してください。')
        mention = message.mentions[0]
        value = Intimacy.get_value(channel_id=cid, user_id=mention.id)
        prompt = intimacy_prompt(value, mention.display_name)
        prompt = prompt[4:-4] if prompt else '中立'
        await message.channel.send(f'`[SYSTEM]` 現在の <@!{mention.id}> に対する親密度は{value}です。({prompt})')
      case _:
        await message.channel.send(
          f"[SYSTEM] `{self.prefix(cid)}debug` 使用法:\n"
          f"・`{self.prefix(cid)}debug console (on | off)` - コンソールデバッグを有効または無効にします。\n"
          f"・`{self.prefix(cid)}debug emotion` - 現在の感情値を表示します。\n",
          f"・`{self.prefix(cid)}debug intimacy [@user]` - 現在の親密度を表示します。\n",
        )

  async def process_command(self, message: Message) -> None:
    cmd, *args = message.content.strip().split(None, 1)
    name = f'cmd_{cmd[len(self.prefix(message.channel.id)):].replace("-", "_")}'
    if hasattr(self, name):
      await getattr(self, name)(message, (args or [''])[0])
    else:
      await message.channel.send(f'`[SYSTEM]` コマンド「{cmd}」は存在しません。')
    return
  
  def is_mentioned(self, message: Message) -> bool:
    return not message.reference and self.client.user in message.mentions or any(
      any(self.client.user == mem._user for mem in role.members) for role in message.role_mentions
    )

  async def on_message(self, message: Message) -> None:
    cid = message.channel.id
    self.latest_message_id[cid] = message.id

    if cid not in self.agents:
      self.init_settings(cid)
      self.emotion_delta[cid] = {}
      self.agents[message.channel.id] = init_agent(
        debug=self.settings[cid]['_debug'],
        conversation_id=cid,
      )

    # 自分のメッセージは無視
    if message.author == self.client.user:
      return

    # メッセージが返信ではなく、メンションがあり、かつメンションに自分が含まれていない場合は無視
    if not message.reference and message.mentions and self.client.user not in message.mentions:
      return

    # メッセージがコマンドプレフィクスから始まる場合はコマンドとして処理
    if message.content.startswith(self.prefix(cid)):
      return await self.process_command(message)

    mentioned = self.is_mentioned(message)

    prev = self.agents[cid].emotion.frozen

    if random() < self.response_ratio(cid) or mentioned:
      async with message.channel.typing():
        text = await self.agents[cid].talk(
          f"{message.author.display_name}:{message.clean_content}",
          injected_system_message=intimacy_prompt(
            Intimacy.get_value(cid, message.author.id),
            message.author.display_name,
          ),
          need_response=True,
        )

      if mentioned or message.reference:
        await message.reply(text)
      elif self.latest_message_id[cid] == message.id:
        await message.channel.send(text)
    else:
      await self.agents[cid].talk(
        f"{message.author.display_name}「{message.clean_content}」",
        need_response=False,
      )

    delta: EmotionDelta = self.agents[cid].emotion.frozen - prev
    if message.author.id in self.emotion_delta[cid]:
      self.emotion_delta[cid][message.author.id] += delta
    else:
      self.emotion_delta[cid][message.author.id] = delta
