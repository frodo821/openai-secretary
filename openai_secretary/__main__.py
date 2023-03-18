import atexit
from os.path import dirname, join, expanduser
from openai_secretary import Agent
from readline import read_history_file, set_history_length, write_history_file

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
  history = join(expanduser("~"), ".oai_secretary", "input_history")

  try:
    read_history_file(history)
  except FileNotFoundError:
    pass

  atexit.register(write_history_file, history)
  set_history_length(1000)

  init_agent()

  while True:
    try:
      message = input('You: ')
      print('Agent:', talk_with_agent(message))
    except KeyboardInterrupt:
      print('Bye!')
      break


main()
