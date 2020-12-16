#external libs
import socket
import threading
import time
import importlib
import pydub
import yaml
# internal libs
from server.client_object import ClientObject
from server.audio_mixers.base import AudioMixerBase
import server.audio_mixers.array_mixer as array_mixer
import server.audio_mixers.pydub_mixer as pydub_mixer
import shared
from sys import exit


class Server:
    def __init__(self, audio_mixer: AudioMixerBase):
        self.ip = socket.gethostbyname(socket.gethostname())
        self.audio_mixer = audio_mixer
        self.audio_mixer_lock = threading.Lock()
        self.voice_port = None
        self.data_port = None
        self.voice_socket = None
        self.data_socket = None
        self.clients = {}
        self.clients_lock = threading.Lock()
        self.command_map = {
            'exit': self.exit_command,
            'help': self.help_command,
            'clients': self.clients_command,
            'update': self.update_settings_command,
            'mixer': self.change_audio_mixer_command,
        }
        self.closing = False
        with open("server/offsets/offsets.yaml", 'r') as f:
            self.offsets = yaml.load(f, Loader=yaml.FullLoader)

    def bind_voice(self, port):
        self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.voice_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.voice_socket.bind((self.ip, port))
        self.voice_socket.listen(shared.MAX_CONCURRENT_CONNECTIONS)
        self.voice_port = port

    def bind_data(self, port):
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.data_socket.bind((self.ip, port))
        self.data_socket.listen(shared.MAX_CONCURRENT_CONNECTIONS)
        self.data_port = port

    def listen(self):
        if self.voice_socket is None or self.data_socket is None:
            raise Exception("You must sucesfully call .bind_voice(port_number) and .bind_data(port_number) before .listen()")

        print('Running on IP: ' + self.ip)
        print('Voice port: ' + str(self.voice_port))
        print('Data port: ' + str(self.data_port))

        threading.Thread(target=self.receive_voice_connections, daemon=True).start()
        threading.Thread(target=self.receive_data_connections, daemon=True).start()
        threading.Thread(target=self.collect_voice, daemon=True).start()

        self.wait_for_commands()

    def wait_for_commands(self):
        print("Accepting new connections. Type help for available commands.")
        while True:
            try:
                cmd = input("$ ")
            except KeyboardInterrupt:
                print("Please run 'exit' instead.")
                continue

            try:
                self.run_command(cmd.split(' '))
            except Exception as e:
                print(str(e))

    def receive_voice_connections(self):
        while not self.closing:
            try:
                socket, _ = self.voice_socket.accept()
                with self.clients_lock:
                    user_id = self.user_id_from_socket(socket)
                    if not user_id:
                        continue
        
                    client = ClientObject(socket, user_id, self.offsets)
                    self.clients[user_id] = client
                    print("Received new voice client: %s" % (client.user_id,))

                    # The client waits for this message after voice connection.
                    # This makes sure we don't attempt data connection before client object is in memory
                    try:
                        socket.send("Ready for data connection!".encode(shared.ENCODING))
                    except:
                        client.close()
            except Exception as e:
                if not self.closing:
                    print("Error in voice connections: %s" % (e,))

    def receive_data_connections(self):
        while not self.closing:
            try:
                socket, addr = self.data_socket.accept()
                str_addr = addr[0] + ':' + str(addr[1])

                print("New data connection from %s" % (str_addr,))

                user_id = self.user_id_from_socket(socket)
                if not user_id:
                    continue

                with self.clients_lock:
                    for client in self.clients.values():
                        if client.user_id == user_id:
                            print("Matching voice socket found! (%s)" % (user_id,))
                            client.set_data_socket(socket)
                            break
                    else:  # loop did not break
                        print("Could not find user_id(%s) from %s, closing socket." % (user_id, str_addr,))
                        socket.close()
            except Exception as e: 
                if not self.closing:
                    print("Error in data connections: %s" % (e,))

    def user_id_from_socket(self, socket):
        try:
            return socket.recv(256).decode(shared.ENCODING)
        except Exception as e:
            print("Error receiving user id: %s" % (e,))
            socket.close()
        return None
            
    def collect_voice(self):
        while not self.closing:
                all_voice_data = {}
                to_remove = []
                with self.clients_lock:
                    if len(self.clients) == 0: 
                        time.sleep(0.1)  # prevent a busy-wait when there are 0 clients connected. 
                        continue

                    for user_id, client in self.clients.items():
                        if client.voice_socket is None:
                            continue
                        try:
                            data = client.voice_socket.recv(shared.BYTES_PER_CHUNK)
                            segment = pydub.AudioSegment(data, sample_width=shared.SAMPLE_WIDTH, frame_rate=shared.SAMPLE_RATE, channels=shared.CHANNELS)
                            all_voice_data[client] = segment
                        except socket.error:
                            print("Removed client %s" % (user_id,))
                            client.close()
                            to_remove.append(user_id)
                            continue

                    for remove in to_remove:
                        del self.clients[remove]
                        
                # No voice to send to anyone else
                if len(all_voice_data) <= 1:
                    continue

                with self.audio_mixer_lock:
                    with self.clients_lock:
                        for client in self.clients.values():
                            self.broadcast_voice(client, all_voice_data)

    def broadcast_voice(self, destination_client: ClientObject, all_voice_data: dict):
        final_audio = self.audio_mixer.mix(destination_client, all_voice_data)
        if final_audio is None:
            return

        try:
            destination_client.voice_socket.send(final_audio)
        except Exception as e:
            print("Error sending final audio: " + str(e))
            destination_client.close()       

    def run_command(self, command):
        if command[0] in self.command_map:
             # pass all the words except the first one, that's the command word itself
            self.command_map[command[0]](command[1:])
        else:
            print('Unknown command :(')

    def exit_command(self, _):
        self.closing = True
        self.data_socket.close()
        self.voice_socket.close()
        exit()

    def help_command(self, _):
        print('Available commands: ')
        for command in self.command_map.keys():
            print(command)

    def clients_command(self, _):
        for client in self.clients:
            print(client)

    def update_settings_command(self, _):
        for client in self.clients.values():
            client.send(shared.ServerSettingsPacket(1, 2))

    def change_audio_mixer_command(self, args):
        mixer_map = {
            'pydub': (pydub_mixer, pydub_mixer.PydubMixer),
            'array': (array_mixer, array_mixer.ArrayMixer),
        }
        importlib.reload(mixer_map[args[0]][0])
        with self.audio_mixer_lock:
            self.audio_mixer = mixer_map[args[0]][1]()