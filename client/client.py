import sounddevice
import socket
import threading
import audioop
import subprocess
import platform
import pickle
import sys
from queue import Queue, Empty
from time import sleep
import sounddevice
import numpy as np
import uuid
from sys import exit

import shared
from client.memory import AmongUsMemory
from client.audio_engines.base import AudioEngineBase

class Client:
    def __init__(self, among_us_memory: AmongUsMemory, audio_engine: AudioEngineBase):
        self.among_us_memory = among_us_memory
        self.audio_engine = audio_engine
        self.exiting = False
        self.ip = None
        self.voice_port = None
        self.data_port = None
        self.user_id = uuid.uuid4()

        self.server_voice_socket = None
        self.server_data_socket = None

        self.send_queue = Queue()

        self.command_map = {
            'help': self.help_command,
            'exit': self.exit_command,
            'ping': self.ping_command,
            'retry': self.retry_command,
        }

        self.packet_handlers = {
            shared.PingPacket: self.ping_packet_handler,
            shared.ServerSettingsPacket: self.server_settings_packet_handler
        }

    def connect(self, ip, voice_port, data_port):
        self.ip = ip
        self.voice_port = voice_port
        self.data_port = data_port

        self.recording_stream = sounddevice.RawInputStream(channels=shared.CHANNELS, blocksize=shared.BYTES_PER_CHUNK, samplerate=shared.SAMPLE_RATE, dtype=np.int16)
        self.playing_stream = sounddevice.RawOutputStream(channels=shared.CHANNELS, blocksize=shared.BYTES_PER_CHUNK, samplerate=shared.SAMPLE_RATE, dtype=np.int16)
        
        self.server_voice_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_voice_socket.connect((ip, voice_port))
        self.server_voice_socket.send(str(self.user_id).encode(shared.ENCODING))

        # The server will respond with a ping msg when it's ready for data
        _ = self.server_voice_socket.recv(1024)

        self.server_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_data_socket.connect((ip, data_port))
        self.server_data_socket.send(str(self.user_id).encode(shared.ENCODING))

        threading.Thread(target=self.receive_server_audio, daemon=True).start()
        threading.Thread(target=self.send_client_audio, daemon=True).start()

        threading.Thread(target=self.receive_server_data, daemon=True).start()
        threading.Thread(target=self.send_client_data, daemon=True).start()
        threading.Thread(target=self.read_memory, daemon=True).start()

    def close(self):
        self.exiting = True

        try:
            self.server_voice_socket.close()
        except: pass

        try:
            self.server_data_socket.close()
        except: pass

        try:
            self.recording_stream.stop()
        except: pass
            
        try:
            self.playing_stream.stop()
        except: pass

    def wait_for_commands(self):
        print("Type help for available commands.")
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

    def receive_server_data(self):
        while True:
            try:
                data = self.server_data_socket.recv(1024)
                packet = pickle.loads(data)
                packet_type = type(packet)
                if packet_type in self.packet_handlers:
                    self.packet_handlers[packet_type](packet)
                else:
                    print("Unknown packet: %s" % (packet,))
            except WindowsError as e:
                if not self.exiting:
                    print("Error with data socket: %s, closing data and voice connections." % (e,))
                    self.server_data_socket.close()
                    self.server_voice_socket.close()
                break
            except Exception as e:
                print("Error parsing packet: %s" % (e,))

    def send_client_data(self):
        while True:
            try:
                object_to_send = self.send_queue.get_nowait()
                val = pickle.dumps(object_to_send, protocol=shared.PICKLE_PROTOCOL)
                self.server_data_socket.sendall(val)
            except Empty:
                sleep(0.1)
            except Exception as e:
                print("Unable to send %s: %s" % (object_to_send, e))
                
    def send(self, packet):
        self.send_queue.put_nowait(packet)

    def receive_server_audio(self):
        self.playing_stream.start()
        while True:
            try:
                voice_data = self.server_voice_socket.recv(shared.BYTES_PER_CHUNK)
                self.playing_stream.write(voice_data)
            except WindowsError as e:
                if not self.exiting:
                    print("Error with voice socket: %s, closing data and voice connections." % (e,))
                    self.server_voice_socket.close()
                    self.server_data_socket.close()
                break
            except Exception as e:
                if not self.exiting:
                    print("Error: " + str(e))
                break

    def send_client_audio(self):
        self.recording_stream.start()
        while True:
            try:
                data = self.recording_stream.read(shared.BYTES_PER_CHUNK)[0]
                rms = audioop.rms(data, 2)
                if rms > 50:
                    self.server_voice_socket.sendall(data)
            except Exception as e:
                self.server_voice_socket.close()
                if not self.exiting:
                    print("Error sending audio: " + str(e))
                break

    def _poll_among_us(self):
        if not self.among_us_memory.open_process():
            print("Waiting for Among Us.exe...")
            while not self.among_us_memory.open_process():
                sleep(1)

        print("Found Among Us.exe!")       

    def read_memory(self):
        self._poll_among_us()

        while True:
            try:
                #self.send(self.audio_engine.get_audio_levels(self.among_us_memory.read()))
                print(self.among_us_memory.read())
                sleep(5)
            except Exception as e:
                print(e)
                sleep(5)
                self._poll_among_us()
            

    def run_command(self, command):
        if command[0] in self.command_map:
             # pass all the words except the first one, that's the command word itself
            self.command_map[command[0]](command[1:])
        else:
            print('Unknown command :(')

    def exit_command(self, args):
        self.exiting = True
        self.close()
        exit()

    def retry_command(self, args):
        self.close()
        self.connect(self.ip, self.voice_port, self.data_port)

    def help_command(self, args):
        print('Available commands: ')
        for command in self.command_map.keys():
            print(command)
    
    def ping_command(self, args):
        self.send(shared.PingPacket())

    def ping_packet_handler(self, packet):
        print("Ping Received!")

    def server_settings_packet_handler(self, packet):
        print(packet)