#external libs
import pickle
import socket
import threading
from time import time, sleep
import importlib
import yaml
# internal libs
from server.client_object import ClientObject
from server.audio_mixers.base import AudioMixerBase
import server.audio_mixers.array_mixer as array_mixer
import shared.consts as consts
import shared.packets as packets
from sys import exit

class Server:
    def __init__(self, audio_mixer: AudioMixerBase):
        self.audio_mixer = audio_mixer
        self.audio_mixer_lock = threading.Lock()
        self.voice_port = None
        self.data_port = None
        self.voice_socket = None
        self.data_socket = None
        self.join_id = 0
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

    def setup_voice(self, port):
        self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.voice_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.voice_socket.bind(("0.0.0.0", port))
        self.voice_port = port

    def setup_data(self, port):
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.data_socket.bind(("0.0.0.0", port))
        self.data_port = port

    def listen(self):
        if self.voice_socket is None or self.data_socket is None:
            raise Exception("You must sucesfully call .setup_voice(port_number) and .setup_data(port_number) before .listen()") 

        print('Voice port: ' + str(self.voice_port))
        print('Data port: ' + str(self.data_port))

        threading.Thread(target=self.receive_voice_loop, daemon=True).start()
        threading.Thread(target=self.receive_data_loop, daemon=True).start()
        threading.Thread(target=self.send_voice_loop, daemon=True).start()

    def send_voice_loop(self):
        while not self.closing:
            print("In voice loop")
            to_remove = []
            voice_data = {}
            cur_time = time()
            with self.clients_lock:
                for client in self.clients.values():
                    if cur_time - client.last_updated > consts.CLEANUP_TIMEOUT:
                        to_remove.append(client)
                        continue
                    client_voice_data = client.read_voice_data()
                    if client_voice_data is not None:
                        voice_data[client] = client_voice_data

                for client in to_remove:
                    print("removed client %d" % (client.join_id,))
                    del self.clients[client.client_id]
                    
            # voice to send to anyone else
            if len(voice_data) > 1:
                with self.audio_mixer_lock and self.clients_lock:
                    for client in self.clients.values():
                        if client.voice_address is None:
                            continue
                        final_audio = self.audio_mixer.mix(client, voice_data)
                        if final_audio is None:
                            continue
                        try:
                            for i in range(0, len(final_audio), consts.PACKET_SIZE):
                                client.send_voice(final_audio[i:i+consts.PACKET_SIZE])
                        except Exception as e:
                            print("Error sending final audio: " + str(e))
            sleep(consts.OUTPUT_BLOCK_TIME)

    def receive_voice_loop(self):
        while not self.closing:
            try:
                data, address = self.voice_socket.recvfrom(consts.PACKET_SIZE)
                packet: packets.ClientVoiceFramePacket = pickle.loads(data)
                client = self.get_client_object(packet.clientId, voice_address=address)
                client.add_voice_data(packet)
            except Exception:
                pass

    def receive_data_loop(self):
        while not self.closing:
            try:
                data, address = self.data_socket.recvfrom(consts.PACKET_SIZE)
                packet: packets.ClientPacket = pickle.loads(data)
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
        self.data_socket.close()
        self.voice_socket.close()

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
            client.send_data(packets.ServerSettingsPacket(1, 2))

    def change_audio_mixer_command(self, args):
        mixer = args[0]
        mixer_map = {
            'array': (array_mixer, 'ArrayMixer'),
        }
        mixer_module, mixer_type_name = mixer_map[mixer]
        loaded_module = importlib.reload(mixer_module)
        mixer_map[mixer] = (loaded_module, mixer_type_name)
        with self.audio_mixer_lock:
            self.audio_mixer = getattr(loaded_module, mixer_type_name)()


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
        if client_id not in self.clients:
            print("Received new client: %d" % (client_id,))
            with self.clients_lock:
                client = ClientObject(client_id,
                                        self.offsets,
                                        self.data_socket,
                                        self.voice_socket,
                                        self.join_id,
                                        voice_address=voice_address,
                                        data_address=data_address)
                self.join_id += 1
                self.clients[client_id] = client
                return client
        else:
            client: ClientObject = self.clients[client_id]
            if client.voice_address is None:
                client.voice_address = voice_address
            elif client.data_address is None:
                client.data_address = data_address
        
        return self.clients[client_id]