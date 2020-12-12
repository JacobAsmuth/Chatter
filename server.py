from server.server import Server  # pylint: disable-msg=E0611
import shared

def main():
    server = Server()
    try:
        server.bind_voice(shared.VOICE_PORT)
        server.bind_data(shared.DATA_PORT)
        server.listen()

    except Exception as e:
        print("Couldn't bind to port: " + str(e))
        
if __name__ == "__main__":
    main()