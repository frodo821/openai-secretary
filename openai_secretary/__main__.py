from openai_secretary import init_agent, talk_with_agent


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
