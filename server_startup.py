from server.server import Server
import shared.consts as consts
from server.audio_mixers.array_mixer import ArrayMixer

import yappi

def main():
    yappi.set_clock_type("cpu")
    yappi.start()
    server = Server(ArrayMixer())
    try:
        server.setup_voice(consts.VOICE_PORT)
        server.setup_data(consts.DATA_PORT)
        server.listen()
        server.wait_for_commands()


    except Exception as e:
        print("Couldn't bind to port: " + str(e))
    except SystemExit:
        pass
        yappi.get_func_stats().print_all()
        yappi.get_thread_stats().print_all()

        
if __name__ == "__main__":
    main()