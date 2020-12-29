import sounddevice
import audioop
import socket
import threading
import pickle
from time import sleep, time
import sounddevice
import numpy as np
import random
from sys import exit
from threading import Lock
import winsound
import keyboard

import shared.consts as consts
import shared.packets as packets
from shared.jitter_buffer import JitterBuffer
from shared.encoder import Encoder
from client.memory import AmongUsMemory, MemoryRead
from client.audio_engines.base import AudioEngineBase

class Client:
    def __init__(self, among_us_memory: AmongUsMemory, audio_engine: AudioEngineBase):
        self.among_us_memory = among_us_memory
        self.audio_engine = audio_engine
        self.closing = False
        self.ip = None
        self.voice_port = None
        self.data_port = None
        self.client_id = random.getrandbits(64)
        self.settings = packets.ClientSettingsPacket()
        self.send_data_lock = Lock()
        self.voice_buffer = None
        self.encoder = None
        self.sent_frames_count = 0
        self.release_frame = -1
        self.release_frame_duration = 3
        self.last_memory_read: MemoryRead = None
        self.imposter_chat = False

        keyboard.hook_key("shift", self.on_shift)

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
            packets.ServerRestartingPacket: self.retry_command,
        }

    def connect(self, ip, voice_port, data_port):
        self.closing = False
        self.sent_frames_count = 0
        self.release_frame = -1
        self.ip = ip
        self.voice_port = voice_port
        self.data_port = data_port
        self.sent_audio = False
        self.encoder = Encoder()
        self.all_audio = bytearray()
        self.voice_buffer = JitterBuffer(consts.MIN_BUFFER_SIZE, consts.MAX_BUFFER_SIZE)

        self.audio_stream = sounddevice.RawStream(blocksize=consts.SAMPLES_PER_FRAME,
                                                    channels=consts.CHANNELS,
                                                    samplerate=consts.SAMPLE_RATE,
                                                    dtype=np.int16,
                                                    callback=self.audio_callback,
                                                )

        self.voice_addr = (self.ip, self.voice_port)
        self.data_addr = (self.ip, self.data_port)
        self.voice_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_data_socket.connect(self.data_addr)
        self.tcp_data_socket.sendall(pickle.dumps(packets.ClientPacket(self.client_id), consts.PICKLE_PROTOCOL))

        offsets_packet = pickle.loads(self.tcp_data_socket.recv(consts.PACKET_SIZE))
        assert type(offsets_packet) == packets.OffsetsPacket

        self.among_us_memory.set_offsets(offsets_packet.offsets)
        self.audio_stream.start()

        # beep beep
        winsound.Beep(300, 80)
        winsound.Beep(350, 90)
        winsound.Beep(400, 200)
        winsound.Beep(500, 200)

        print("Connected to server, initializing...") 
        threading.Thread(target=self.receive_audio_loop, daemon=True).start()
        threading.Thread(target=self.read_memory_loop, daemon=True).start()
        threading.Thread(target=self.receive_tcp_data_loop, daemon=True).start()

    def close(self):
        self.closing = True

        try:
            self.voice_socket.close()
        except: pass

        try:
            self.udp_data_socket.close()
        except: pass

        try:
            self.audio_stream.stop()
        except: pass
            
    def wait_for_commands(self):
        print("Type help for available commands.")
        while not self.closing:
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
        while not self.closing:
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
                if not self.closing:
                    print("Error with data socket: %s, closing connections." % (e,))
                    self.close()
                break
            except Exception as e:
                if not self.closing:
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
            if not self.closing:
                self.close()
                print("Server died: %s" % (e,))
        except Exception as e:
            print("Unable to send %s: %s" % (packet, e))

    def receive_audio_loop(self):
        while self.sent_frames_count == 0:
            sleep(0.1)

        while not self.closing:
            try:
                raw_bytes, _ = self.voice_socket.recvfrom(consts.PACKET_SIZE)
                packet: packets.ServerVoiceFramePacket = pickle.loads(raw_bytes)
                self.voice_buffer.add_frame(packet.frameId, packet.voiceFrame)
            except Exception as e:
                if not self.closing:
                    self.close()
                    print("Error receiving audio: " + str(e))
                break

    def audio_callback(self, indata, outdata, frames: int, time_, status):
        rms = audioop.rms(indata, consts.BYTES_PER_SAMPLE)
        if rms < 200:
            audio = bytes(len(indata))
        elif self.sent_frames_count <= self.release_frame:
            audio = bytes(indata)
        else:
            audio = bytes(indata)
            self.release_frame = self.sent_frames_count + self.release_frame_duration

        packet = packets.ClientVoiceFramePacket(frameId=time(), clientId=self.client_id, voiceFrame=self.encoder.encode(audio))
        packet_bytes = pickle.dumps(packet, protocol=consts.PICKLE_PROTOCOL)
        if not self.closing:
            self.voice_socket.sendto(packet_bytes, self.voice_addr)
            self.sent_frames_count += 1

        samples = self.voice_buffer.get_samples()
        if samples is not None and self.muted is False:
            outdata[:] = self.encoder.decode(samples)
        else:
            outdata[:] = bytes(len(outdata))

    def _poll_among_us(self):
        if not self.among_us_memory.open_process():
            print("Waiting for Among Us.exe...")
            while not self.among_us_memory.open_process():
                sleep(1)

        print("Found Among Us.exe!")       

    def read_memory_and_send(self):
        memory_read = self.among_us_memory.read()
        if memory_read.local_player:
            names, gains = self.audio_engine.get_audio_levels(memory_read, self.settings)

            self.send(packets.AudioLevelsPacket(clientId=self.client_id,
                                                playerName=memory_read.local_player.name,
                                                playerNames=names,
                                                gains=gains), tcp=False)
        self.last_memory_read = memory_read

    def read_memory_loop(self):
        self._poll_among_us()

        while not self.closing:
            try:
                self.read_memory_and_send()
                sleep(0.05)
            except Exception:
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

    def on_shift(self, e):
        if e.event_type == keyboard.KEY_DOWN:
            if self.last_memory_read \
              and self.last_memory_read.local_player \
              and self.last_memory_read.local_player.impostor \
              and self.settings.imposter_voice_allowed:
                self.imposter_chat = True
        else:  # key up
            self.imposter_chat = False
