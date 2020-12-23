import sounddevice
import socket
import threading
import pickle
from time import sleep, time
import sounddevice
import numpy as np
import random
from sys import exit
import audioop
from threading import Lock
from shared.jitter_buffer import JitterBuffer

import shared.consts as consts
import shared.packets as packets
from client.memory import AmongUsMemory
from client.audio_engines.base import AudioEngineBase

class Client:
    def __init__(self, among_us_memory: AmongUsMemory, audio_engine: AudioEngineBase):
        self.among_us_memory = among_us_memory
        self.audio_engine = audio_engine
        self.exiting = False
        self.sent_audio = False
        self.ip = None
        self.voice_port = None
        self.data_port = None
        self.client_id = random.getrandbits(64)
        self.settings = packets.ClientSettingsPacket()
        self.encoding_state = None
        self.decoding_state = None
        self.send_data_lock = Lock()
        self.voice_buffer = JitterBuffer(consts.MIN_BUFFER_SIZE, consts.MAX_BUFFER_SIZE)

        self.muted = False
        self.voice_socket = None
        self.udp_data_socket = None

        self.command_map = {
            'help': self.help_command,
            'exit': self.exit_command,
            'retry': self.retry_command,
            'volume': self.volume_command,
            'mute': self.mute_command,
        }

        self.packet_handlers = {
            packets.ClientSettingsPacket: self.client_settings_packet_handler,
            packets.OffsetsResponsePacket: self.offsets_response_packet_handler,
            packets.ServerRestartingPacket: self.retry_command,
        }

    def connect(self, ip, voice_port, data_port):
        self.exiting = False
        self.ip = ip
        self.voice_port = voice_port
        self.data_port = data_port
        self.sent_audio = False

        self.recording_stream = sounddevice.RawInputStream(channels=consts.CHANNELS, samplerate=consts.SAMPLE_RATE, dtype=np.int16)
        self.playing_stream = sounddevice.RawOutputStream(channels=consts.CHANNELS, samplerate=consts.SAMPLE_RATE, dtype=np.int16)

        self.voice_addr = (self.ip, self.voice_port)
        self.data_addr = (self.ip, self.data_port)
        self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_data_socket.connect(self.data_addr)
        self.tcp_data_socket.sendall(pickle.dumps(packets.ClientPacket(self.client_id), consts.PICKLE_PROTOCOL))

        _ = self.tcp_data_socket.recv(len(consts.ACK_MSG))

        print("Connected to server, initializing...") 
        threading.Thread(target=self.send_audio_loop, daemon=True).start()
        threading.Thread(target=self.receive_audio_loop, daemon=True).start()

        threading.Thread(target=self.read_memory_loop, daemon=True).start()
        threading.Thread(target=self.receive_tcp_data_loop, daemon=True).start()
        threading.Thread(target=self.play_audio_loop, daemon=True).start()

    def close(self):
        self.exiting = True

        try:
            self.voice_socket.close()
        except: pass

        try:
            self.udp_data_socket.close()
        except: pass

        try:
            self.recording_stream.stop()
        except: pass
            
        try:
            self.playing_stream.stop()
        except: pass

        try:
            while not self.send_queue.empty():
                self.send_queue.get_nowait()
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


    def receive_tcp_data_loop(self):
        while not self.exiting:
            try:
                packet_bytes = self.tcp_data_socket.recv(consts.PACKET_SIZE)
                if len(packet_bytes) == 0:
                    self.close()

                packet = pickle.loads(packet_bytes)
                packet_type = type(packet)

                if packet_type in self.packet_handlers:
                    self.packet_handlers[packet_type](packet)
                else:
                    print("Unknown packet: %s" % (packet,))

            except WindowsError as e:
                if not self.exiting:
                    print("Error with data socket: %s, closing connections." % (e,))
                    self.close()
                break
            except Exception as e:
                if not self.exiting:
                    self.close()
                    print("Error parsing packet: %s" % (e,))
                break

    def send(self, packet, tcp=True):
        try:
            packet_bytes = pickle.dumps(packet, protocol=consts.PICKLE_PROTOCOL)
            if tcp:
                self.tcp_data_socket.sendall(packet_bytes)
            else:
                self.udp_data_socket.sendto(packet_bytes, self.data_addr)
                self.sent_data = True
        except WindowsError as e:
            if not self.exiting:
                self.close()
                print("Server died: %s" % (e,))
        except Exception as e:
            print("Unable to send %s: %s" % (packet, e))
                
    def send_audio_loop(self):
        self.recording_stream.start()

        while not self.exiting:
            try:
                raw_audio, _ = self.recording_stream.read(consts.SAMPLES_PER_FRAME)

                encoded_audio, self.encoding_state = audioop.lin2adpcm(raw_audio, consts.BYTES_PER_SAMPLE, self.encoding_state)
                packet = packets.ClientVoiceFramePacket(frameId=time(), clientId=self.client_id, voiceFrame=encoded_audio)
                packet_bytes = pickle.dumps(packet, protocol=consts.PICKLE_PROTOCOL)

                self.voice_socket.sendto(packet_bytes, self.voice_addr)
                self.sent_audio = True
            except Exception as e:
                if not self.exiting:
                    self.close()
                    print("Error sending audio: " + str(e))

    def receive_audio_loop(self):
        while not self.sent_audio:
            sleep(0.1)

        while not self.exiting:
            try:
                raw_bytes, _ = self.voice_socket.recvfrom(consts.PACKET_SIZE)
                packet: packets.ServerVoiceFramePacket = pickle.loads(raw_bytes)
                decoded_voice, self.decoding_state = audioop.adpcm2lin(packet.voiceFrame, consts.BYTES_PER_SAMPLE, self.decoding_state)
                self.voice_buffer.add_frame(packet.frameId, decoded_voice)
            except WindowsError as e:
                if not self.exiting:
                    self.close()
                    print("Error with voice socket: %s, closing data and voice connections." % (e,))
                break
            except Exception as e:
                if not self.exiting:
                    self.close()
                    print("Error receiving audio: " + str(e))
                break

    def play_audio_loop(self):
        self.playing_stream.start()
        while not self.exiting:
            samples = self.voice_buffer.get_samples()
            if samples is not None and not self.muted:
                self.playing_stream.write(samples)
            sleep(0.01)

    def _poll_among_us(self):
        if not self.among_us_memory.open_process():
            print("Waiting for Among Us.exe...")
            while not self.among_us_memory.open_process():
                sleep(1)

        print("Found Among Us.exe!")       

    def _get_offsets(self):
        print("Asking for offsets from server...")
        self.send(packets.OffsetsRequestPacket())
        while not self.among_us_memory.has_offsets():
            sleep(2)
            self.send(packets.OffsetsRequestPacket())  # gotta resend, packet might've been dropped

    def read_memory_and_send(self):
        memory_read = self.among_us_memory.read()
        if memory_read.local_player:
            names, gains = self.audio_engine.get_audio_levels(memory_read, self.settings)

            self.send(packets.AudioLevelsPacket(clientId=self.client_id,
                                                playerName=memory_read.local_player.name,
                                                playerNames=names,
                                                gains=gains), tcp=False)

    def read_memory_loop(self):
        self._get_offsets()
        self._poll_among_us()

        while not self.exiting:
            try:
                self.read_memory_and_send()
                sleep(0.05)
            except Exception as e:
                print("Error in memory loop: %s" % (e,))
                sleep(5)
                self._poll_among_us()
            
    def run_command(self, command):
        if command[0] in self.command_map:
             # pass all the words except the first one, that's the command word itself
            self.command_map[command[0]](command[1:])
        else:
            print('Unknown command :(')

    def exit_command(self, _):
        self.close()
        exit()

    def retry_command(self, _):
        self.close()
        print("Reconnecting")
        sleep(consts.CLEANUP_TIMEOUT + 3)
        self.connect(self.ip, self.voice_port, self.data_port)

    def help_command(self, _):
        print('Available commands: ')
        for command in self.command_map.keys():
            print(command)
    
    def volume_command(self, args):
        self.send(packets.VolumePacket(float(args[0])))

    def mute_command(self, _):
        self.muted = not self.muted

    def client_settings_packet_handler(self, packet: packets.ClientSettingsPacket):
        for field in packet.__dataclass_fields__:
             val = getattr(packet, field)
             if val is not None:
                 setattr(self.settings, field, val)

    def offsets_response_packet_handler(self, packet: packets.OffsetsResponsePacket):
        self.among_us_memory.set_offsets(packet.offsets)