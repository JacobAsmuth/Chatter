import sys
from client.client import Client
import client.memory as memory
import shared.consts as consts
from client.audio_engines.linear import Linear

from client.overlay import OverlayUi

def main(args):
    #import yappi
    #yappi.set_clock_type("cpu")
    #yappi.start()

    mem = memory.AmongUsMemory()
    linear_audio = Linear()

    try:
        client = Client(mem, linear_audio)
        if len(args) == 0:
            client.connect(consts.SERVER_AWS_IP, consts.VOICE_PORT, consts.DATA_PORT)
        else:
            client.connect(args[0], consts.VOICE_PORT, consts.DATA_PORT)

        #OverlayUi(client, daemon=True).start()
        client.wait_for_commands()
    except SystemExit:
        pass
        #yappi.get_func_stats().print_all()
        #yappi.get_thread_stats().print_all()


if __name__ == "__main__":
    main(sys.argv[1:])
