import atexit
from os.path import join, expanduser
import sys
from openai_secretary import init_agent
from readline import read_history_file, set_history_length, write_history_file


def main():
  history = join(expanduser("~"), ".oai_secretary", "input_history")

  try:
    read_history_file(history)
  except FileNotFoundError:
    pass

  atexit.register(write_history_file, history)
  set_history_length(1000)

  agent = init_agent(debug="--debug" in sys.argv)

  while True:
    try:
      message = input('You: ')
      print('Agent:', agent.talk(message))
    except KeyboardInterrupt:
      print('Bye!')
      break


main()
