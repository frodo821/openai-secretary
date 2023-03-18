from random import random
from typing import Any
from discord.flags import Intents
from discord.client import Client
from discord.message import Message
from openai_secretary import Agent, init_agent


def registerHandlers(impl: Any, client: Client) -> None:
  for attr in (attr for attr in dir(impl) if attr.startswith('on_')):
    client.event(getattr(impl, attr))


class OpenAIChatBot:
  client: Client
  agent: Agent
  response_ratio: float
  __secret: str
  cmd_prefix: str = '!'

  def __init__(self, secret: str, *, response_ratio=0.2) -> None:
    intents = Intents.default()
    intents.message_content = True

    self.client = Client(intents=intents)
    self.agent = init_agent(debug=False)
    self.__secret = secret
    self.response_ratio = response_ratio
    registerHandlers(self, self.client)

  def start(self) -> None:
    self.client.run(self.__secret)

  async def on_ready(self) -> None:
    print(f'Logged in as {self.client.user}')

  async def cmd_response_ratio(self, message: Message, args: str) -> None:
    if not args:
      await message.channel.send(f'`[SYSTEM]` 現在の返答率は{self.response_ratio}です。')
      return

    self.response_ratio = float(args)
    await message.channel.send(f'`[SYSTEM]` 返答率を{self.response_ratio}に更新しました。')

  async def cmd_initial_prompt(self, message: Message, args: str) -> None:
    if not args:
      await message.channel.send(f'`[SYSTEM]` 現在の初期プロンプトは「{self.agent.initial_message}」です。')
      return

    self.agent.initial_message = args
    await message.channel.send(f'`[SYSTEM]` 初期プロンプトを「{self.agent.initial_message}」に更新しました。')

  async def cmd_debug(self, message: Message, args: str) -> None:
    if not args:
      await message.channel.send(f'`[SYSTEM]` 現在のデバッグモードは{"有効" if self.agent._debug else "無効"}です。')
      return

    match args.split():
      case ['console', 'on']:
        self.agent._debug = True
        await message.channel.send(f'`[SYSTEM]` コンソールデバッグを有効に切り替えました。')
      case ['console', 'off']:
        self.agent._debug = False
        await message.channel.send(f'`[SYSTEM]` コンソールデバッグを無効に切り替えました。')
      case ['emotion']:
        await message.channel.send(f'`[SYSTEM]` 現在の感情は{repr(self.agent.emotion)}です。')

  async def on_message(self, message: Message) -> None:
    if message.author == self.client.user:
      return

    if message.mentions and self.client.user not in message.mentions:
      return

    if message.content.startswith(self.cmd_prefix):
      cmd, *args = message.content.strip().split(None, 1)
      name = f'cmd_{cmd[1:].replace("-", "_")}'
      if hasattr(self, name):
        await getattr(self, name)(message, (args or [''])[0])
      else:
        await message.channel.send(f'`[SYSTEM]` コマンド「{cmd}」は存在しません。')
      return

    mentioned = self.client.user in message.mentions

    if random() < self.response_ratio or mentioned:
      await message.channel.typing()
      text = self.agent.talk(
        f"{message.author.display_name}「{message.content}」",
        need_response=True,
      )

      if mentioned:
        await message.reply(text)
      else:
        await message.channel.send(text)
    else:
      self.agent.talk(
        f"{message.author.display_name}「{message.content}」",
        need_response=False,
      )
