import sys
from client import Client
import client.memory as memory
import shared

def main(args):
    mem = memory.AmongUsMemory()

    client = Client(mem)
    client.connect(args[0], shared.VOICE_PORT, shared.DATA_PORT)
    client.wait_for_commands()


if __name__ == "__main__":
    main(sys.argv[1:])
