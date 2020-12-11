#external libs
import socket
import threading
import numpy as np
import pickle
import queue
import time
import pydub
# internal libs
from client_object import ClientObject
import shared
import io
from sys import exit


class Server:
    def __init__(self):
        self.TEMP_GAIN = 1
        self.ip = socket.gethostbyname(socket.gethostname())
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
            'gain': self.temp_gain_command,
        }

    def bind_voice(self, port):
        self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.voice_socket.bind((self.ip, port))
        self.voice_socket.listen(shared.MAX_CONCURRENT_CONNECTIONS)
        self.voice_port = port

    def bind_data(self, port):
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
        while True:
            socket, _ = self.voice_socket.accept()
            with self.clients_lock:
                user_id = self.user_id_from_socket(socket)
    
                client = ClientObject(socket, user_id)
                self.clients[user_id] = client
                print("Received new voice client: %s" % (client.user_id,))

                # The client waits for this message after voice connection.
                # This makes sure we don't attempt data connection before client object is in memory
                socket.send("Ready for data connection!".encode(shared.ENCODING))

    def receive_data_connections(self):
        while True:
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

    def user_id_from_socket(self, socket):
        try:
            return socket.recv(256).decode(shared.ENCODING)
        except Exception as e:
            print("Error receiving user id: %s" % (e,))
            socket.close()
        return None
            
    def collect_voice(self):
        while True:
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
                            #segment = pydub.AudioSegment(data).set_frame_rate(48000).set_channels(2).set_sample_width(2)
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

                with self.clients_lock:
                    for client in self.clients.values():
                        self.broadcast_voice(client, all_voice_data)

    def broadcast_voice(self, destination_client: ClientObject, all_voice_data: dict):

        final_audio = None

        for source_client, source_audio in all_voice_data.items():
            if source_client is destination_client:
                continue

            gain = destination_client.audio_levels_map[source_client.player_id] or self.TEMP_GAIN

            if gain != 0:
                #new_audio = source_audio - gain  # gain is in percent. Log10(gain) converts to DB.
                if final_audio:
                    #source_audio = source_audio.apply_gain(np.log10(gain*100))
                    final_audio = final_audio.overlay(source_audio)
                else:
                    final_audio = source_audio

        if not final_audio:
            return

        try:
            destination_client.voice_socket.send(final_audio.raw_data)
        except Exception as e:
            print("Error: " + str(e))

    def run_command(self, command):
        if command[0] in self.command_map:
             # pass all the words except the first one, that's the command word itself
            self.command_map[command[0]](command[1:])
        else:
            print('Unknown command :(')

    def exit_command(self, args):
        self.data_socket.close()
        self.voice_socket.close()
        exit()

    def help_command(self, args):
        print('Available commands: ')
        for command in self.command_map.keys():
            print(command)

    def clients_command(self, args):
        for client in self.clients:
            print(client)

    def update_settings_command(self, args):
        for client in self.clients.values():
            client.send(shared.ServerSettingsPacket(1, 2))
                
    def temp_gain_command(self, args):
        self.TEMP_GAIN = float(args[0])

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