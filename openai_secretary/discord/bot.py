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
    self.agent = init_agent()
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

    if random() < self.response_ratio or self.client.user in message.mentions:
      await message.channel.typing()
      await message.channel.send(
        self.agent.talk(
          f"{message.author.display_name}「{message.content}」",
          need_response=True,
        ),
      )
    else:
      self.agent.talk(
        f"{message.author.display_name}「{message.content}」",
        need_response=False,
      )
