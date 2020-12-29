import shared.consts as consts
import shared.packets as packets
from shared.jitter_buffer import JitterBuffer
from shared.encoder import Encoder

from typing import Union
from time import time
import collections
import socket
import pickle
import audioop
import threading

class ClientObject:
    def __init__(self, client_id: str, offsets: str, tcp_data_socket: socket.socket, udp_data_socket: socket.socket, voice_socket: socket.socket,
                join_id: int, voice_address=None, data_address=None):
        self.voice_address = voice_address
        self.data_address = data_address
        self.join_id = join_id
        self.tcp_data_socket = tcp_data_socket
        self.udp_data_socket = udp_data_socket
        self.voice_socket = voice_socket
        self.client_id = client_id
        self.offsets = offsets
        self.closing = False
        self.player_name = None  # AmongUs In-game name
        self.voice_buffer = JitterBuffer(consts.MIN_BUFFER_SIZE, consts.MAX_BUFFER_SIZE)
        self.audio_levels_map = collections.defaultdict(float)
        self.packet_handlers = {
            packets.AudioLevelsPacket: self.audio_levels_packet_handler,
            packets.VolumePacket: self.volume_packet_handler,
        }
        self.last_updated = time()
        self.volume = 1.0
        self.encoder = Encoder()

        threading.Thread(target=self.receive_tcp_data, daemon=True).start()

    def close(self):
        self.closing = True
        try:
            self.tcp_data_socket.close()
        except : pass

    def receive_tcp_data(self):
        while not self.closing:
            try:
                raw_bytes = self.tcp_data_socket.recv(consts.PACKET_SIZE)
                packet = pickle.loads(raw_bytes)
                self.handle_packet(packet)
            except Exception as e: 
                if not self.closing:
                    print("Error in tcp data connection: %s" % (e,))
                    self.close()

    def send_voice(self, frame) -> None:
        packet = packets.ServerVoiceFramePacket(time(), self.encoder.encode(frame))
        packet_bytes = pickle.dumps(packet, protocol=consts.PICKLE_PROTOCOL)
        self.voice_socket.sendto(packet_bytes, self.voice_address)

    def send(self, packet) -> None:
        packet_bytes = pickle.dumps(packet, protocol=consts.PICKLE_PROTOCOL)
        self.tcp_data_socket.send(packet_bytes)

    def add_voice_frame(self, packet: packets.ClientVoiceFramePacket) -> None:
        self.last_updated = time()
        self.voice_buffer.add_frame(packet.frameId, packet.voiceFrame)

    def read_voice_frame(self) -> Union[bytes, None]:
        samples = self.voice_buffer.get_samples()
        if samples is None:
            return None
        return self.encoder.decode(samples)

    def handle_packet(self, packet) -> None:
        packet_type = type(packet)
        if packet_type not in self.packet_handlers:
            raise ValueError("Unknown packet type: %s" % (type(packet),))

        self.packet_handlers[packet_type](packet)

    def audio_levels_packet_handler(self, packet: packets.AudioLevelsPacket) -> None:
        self.player_name = packet.playerName
        for player_name, gain in zip(packet.playerNames, packet.gains):
            self.audio_levels_map[player_name] = gain

    def volume_packet_handler(self, packet: packets.VolumePacket) -> None:
        self.volume = packet.volume