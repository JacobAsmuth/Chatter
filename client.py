import sys
from client.client import Client # pylint: disable-msg=E0611
import client.memory as memory
import shared
from client.audio_engines.linear import Linear # pylint: disable-msg=E0611


def main(args):
    mem = memory.AmongUsMemory()
    linear_audio = Linear()

    client = Client(mem, linear_audio)
    client.connect(args[0], shared.VOICE_PORT, shared.DATA_PORT)
    client.wait_for_commands()


if __name__ == "__main__":
    main(sys.argv[1:])
