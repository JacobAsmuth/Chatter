#external libs
import pickle
import socket
import threading
from time import time, sleep
import yaml
# internal libs
from server.client_object import ClientObject
from server.audio_mixers.base import AudioMixerBase
from server.settings import Settings
import server.audio_mixers.array_mixer as array_mixer
import shared.consts as consts
import shared.packets as packets
from sys import exit
import os

class Server:
    def __init__(self, audio_mixer: AudioMixerBase):
        self.audio_mixer = audio_mixer
        self.audio_mixer_lock = threading.Lock()
        self.voice_port = None
        self.data_port = None
        self.voice_socket = None
        self.udp_data_socket = None
        self.join_id = 0
        self.clients = {}
        self.clients_lock = threading.Lock()
        self.command_map = {
            'exit': self.exit_command,
            'help': self.help_command,
            'clients': self.clients_command,
            'update': self.update_settings_command,
            'mixer': self.change_audio_mixer_command,
            'ignoregain': self.toggle_ignore_gain_command,
        }
        self.closing = False
        with open("server/offsets/offsets.yaml", 'r') as f:
            self.offsets = yaml.load(f, Loader=yaml.FullLoader)
        self.settings_filepath = consts.SERVER_SETTINGS_FILE
        self.settings = self._try_load_settings()

    def setup_voice(self, port):
        self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.voice_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.voice_socket.bind(("0.0.0.0", port))
        self.voice_port = port

    def setup_data(self, port):
        self.udp_data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_data_socket.bind(("0.0.0.0", port))
        
        self.tcp_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_data_socket.bind(("0.0.0.0", port))

        self.data_port = port

    def listen(self):
        if self.voice_socket is None or self.udp_data_socket is None:
            raise Exception("You must sucesfully call .setup_voice(port_number) and .setup_data(port_number) before .listen()") 

        print('Voice port: ' + str(self.voice_port))
        print('Data port: ' + str(self.data_port))

        self.tcp_data_socket.listen(consts.MAX_CONCURRENT_CONNECTIONS)
        threading.Thread(target=self.receive_tcp_connections_loop, daemon=True).start()

        threading.Thread(target=self.receive_voice_loop, daemon=True).start()
        threading.Thread(target=self.receive_udp_data_loop, daemon=True).start()
        threading.Thread(target=self.send_voice_loop, daemon=True).start()

    def send_voice_loop(self):
        while not self.closing:
            to_remove = []
            voice_frames = {}
            cur_time = time()
            with self.clients_lock:
                for client in self.clients.values():
                    if cur_time - client.last_updated > consts.CLEANUP_TIMEOUT:
                        to_remove.append(client)
                        continue
                    client_voice_frame = client.read_voice_frame()
                    if client_voice_frame is not None:
                        voice_frames[client] = client_voice_frame

                for client in to_remove:
                    print("removed client %d" % (client.join_id,))
                    client.close()
                    del self.clients[client.client_id]
                    
            # voice to send to anyone else
            if len(voice_frames) > 1:
                with self.audio_mixer_lock and self.clients_lock:
                    for client in self.clients.values():
                        if client.voice_address is None:
                            continue
                        final_audio = self.audio_mixer.mix(client, voice_frames, self.settings)
                        if final_audio is None:
                            continue
                        try:
                            for i in range(0, len(final_audio), consts.PACKET_SIZE):
                                client.send_voice(final_audio[i:i+consts.PACKET_SIZE])
                        except Exception as e:
                            print("Error sending final audio: " + str(e))
            sleep(consts.OUTPUT_BLOCK_TIME * 0.9)

    def receive_voice_loop(self):
        while not self.closing:
            try:
                raw_bytes, address = self.voice_socket.recvfrom(consts.PACKET_SIZE)
                packet: packets.ClientVoiceFramePacket = pickle.loads(raw_bytes)
                client = self.get_client_object(packet.clientId, voice_address=address)
                client.add_voice_frame(packet)
            except Exception:
                pass

    def handle_new_client_sockets(self, tcp_data_socket: socket.socket):
        try:
            tcp_data_socket.settimeout(5)
            raw_bytes = tcp_data_socket.recv(consts.PACKET_SIZE)
            tcp_data_socket.settimeout(None)
            client_packet: packets.ClientPacket = pickle.loads(raw_bytes)
            if type(client_packet) != packets.ClientPacket:
                raise Exception("Invalid packet type: %s" % (type(client_packet)))


            with self.clients_lock:
                tcp_data_socket.sendall(consts.ACK_MSG)

                client = ClientObject(client_packet.clientId,
                                        self.offsets,
                                        tcp_data_socket,
                                        self.udp_data_socket,
                                        self.voice_socket,
                                        self.get_next_join_id())
                print("Received new client: %d" % (client.join_id,))
                self.clients[client_packet.clientId] = client
        except Exception as e:
            print("Failed to accept new client: %s" % (e,))

    def receive_tcp_connections_loop(self):
        while not self.closing:
            try:
                client_socket, _ = self.tcp_data_socket.accept()
                threading.Thread(target=self.handle_new_client_sockets, args=(client_socket,)).start()
            except Exception as e:
                if not self.closing:
                    print("Error receving new client: %s" % (e,))
    
    def receive_udp_data_loop(self):
        while not self.closing:
            try:
                raw_bytes, address = self.udp_data_socket.recvfrom(consts.PACKET_SIZE)
                packet: packets.ClientPacket = pickle.loads(raw_bytes)
                client = self.get_client_object(packet.clientId, data_address=address)
                client.handle_packet(packet)
            except Exception as e: 
                if not self.closing:
                    print("Error in data connections: %s" % (e,))

    def run_command(self, command):
        if command[0] in self.command_map:
             # pass all the words except the first one, that's the command word itself
            self.command_map[command[0]](command[1:])
        else:
            print('Unknown command :(')

    def close(self):
        self.closing = True
        for client in self.clients.values():
            client.close()
        self.tcp_data_socket.close()
        self.udp_data_socket.close()
        self.voice_socket.close()

    def restarting(self):
        for client in self.clients.values():
            client.send(packets.ServerRestartingPacket())
        self.close()

    def exit_command(self, _):
        self.close()
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
            client.send_data(packets.ServerSettingsPacket(1, 2, 3))

    def change_audio_mixer_command(self, args):
        mixer_map = {
            'array': (array_mixer.ArrayMixer),
        }
        with self.audio_mixer_lock:
            self.audio_mixer = mixer_map[args[0]]()

    def toggle_ignore_gain_command(self, _):
        self.settings.ignore_client_gain = not self.settings.ignore_client_gain
        self.save_settings()

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

    def get_client_object(self, client_id: int, voice_address=None, data_address=None) -> ClientObject:
        try:
            client: ClientObject = self.clients[client_id]
            if client.voice_address is None:
                client.voice_address = voice_address
            elif client.data_address is None:
                client.data_address = data_address
        except KeyError:
            raise Exception("Unknown client: %d" % (client_id,))
        return client

    def get_next_join_id(self):
        self.join_id += 1
        return self.join_id - 1

    def _try_load_settings(self) -> Settings:
        if os.path.isfile(self.settings_filepath):
            with open(self.settings_filepath, 'rb') as f:
                try:
                    return pickle.load(f)
                except:
                    pass
        return Settings()

    def save_settings(self) -> None:
        with open(self.settings_filepath, 'wb') as f:
            pickle.dump(self.settings, f, protocol=consts.PICKLE_PROTOCOL)