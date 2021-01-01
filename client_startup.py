import sys
from client.client import Client
import client.memory as memory
import shared.consts as consts
from client.audio_engines.linear import Linear

def main(args):
    mem = memory.AmongUsMemory()
    linear_audio = Linear()

    try:
        client = Client(mem, linear_audio)
        if len(args) == 0:
            client.connect(consts.SERVER_AWS_IP, consts.VOICE_PORT, consts.DATA_PORT)
        else:
            client.connect(args[0], consts.VOICE_PORT, consts.DATA_PORT)

        client.wait_for_commands()
    except SystemExit:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])