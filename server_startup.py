from server.server import Server
import shared
from server.audio_mixers.pydub_mixer import PydubMixer
from server.audio_mixers.array_mixer import ArrayMixer

def main():
    server = Server(ArrayMixer())
    try:
        server.bind_voice(shared.VOICE_PORT)
        server.bind_data(shared.DATA_PORT)
        server.listen()

    except Exception as e:
        print("Couldn't bind to port: " + str(e))
        
if __name__ == "__main__":
    main()