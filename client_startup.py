import sys
from client.client import Client
import client.memory as memory
import shared
from client.audio_engines.linear import Linear


def main(args):
    mem = memory.AmongUsMemory()
    linear_audio = Linear()

    client = Client(mem, linear_audio)
    client.connect(args[0], shared.VOICE_PORT, shared.DATA_PORT)
    client.wait_for_commands()


if __name__ == "__main__":
    main(sys.argv[1:])
