from os.path import dirname, join
from openai_secretary import Agent

agent: Agent


def init_agent() -> Agent:
  global agent

  with open(join(dirname(__file__), '..', '.secret')) as f:
    key = f.read().strip()

  agent = Agent(key)

  return agent


def talk_with_agent(message: str) -> str:
  return agent.talk(message)


def main():
  init_agent()

  while True:
    try:
      message = input('You: ')
      print('Agent:', talk_with_agent(message))
    except KeyboardInterrupt:
      print('Bye!')
      break


main()
