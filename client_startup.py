import sys
from client.client import Client
import client.memory as memory
import shared.consts as consts
from client.audio_engines.linear import Linear

#
def main(args):
    mem = memory.AmongUsMemory()
    linear_audio = Linear()

    client = Client(mem, linear_audio)
    if len(args) == 0:
        ip = input("Please enter the IP address to connect to: ")
        client.connect(ip, consts.VOICE_PORT, consts.DATA_PORT)
    else:
        client.connect(args[0], consts.VOICE_PORT, consts.DATA_PORT)
    client.wait_for_commands()


if __name__ == "__main__":
    main(sys.argv[1:])
