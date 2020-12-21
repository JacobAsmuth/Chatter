import shared.consts as consts
import shared.packets as packets
from time import time
import collections
import io
import socket
import pickle
import audioop

class ClientObject:
    def __init__(self, client_id: str, offsets: str, data_socket: socket.socket, voice_socket: socket.socket, join_id: int, voice_address=None, data_address=None):
        self.voice_address = voice_address
        self.data_address = data_address
        self.join_id = join_id
        self.data_socket = data_socket
        self.voice_socket = voice_socket
        self.client_id = client_id
        self.encoding_state = None
        self.decoding_state = None
        self.offsets = offsets
        self.player_id = None  # In-game player ID
        #self.voice_data = io.BytesIO()
        self.voice_data = bytes()
        self.audio_levels_map = collections.defaultdict(float)
        self.packet_handlers = {
            packets.AudioLevelsPacket: self.audio_levels_packet_handler,
            packets.OffsetsRequestPacket: self.offsets_request_packet_handler,
            packets.VolumePacket: self.volume_packet_handler,
        }
        self.last_updated = time()
        self.volume = 1.0
        self.frame_id = 0

    def send_voice(self, data) -> None:
        encoded_audio, self.encoding_state = audioop.lin2adpcm(data, consts.BYTES_PER_SAMPLE, self.encoding_state)
        packet = packets.ServerVoiceFramePacket(self.frame_id, encoded_audio)
        packet_bytes = pickle.dumps(packet, protocol=consts.PICKLE_PROTOCOL)
        self.voice_socket.sendto(packet_bytes, self.voice_address)
        self.frame_id += 1

    def send_data(self, packet) -> None:
        packet_bytes = pickle.dumps(packet, protocol=consts.PICKLE_PROTOCOL)
        self.data_socket.sendto(packet_bytes, self.data_address)

    def add_voice_data(self, packet: packets.ClientVoiceFramePacket) -> None:
        self.last_updated = time()
        decoded, self.decoding_state = audioop.adpcm2lin(packet.voiceData, consts.BYTES_PER_SAMPLE, self.decoding_state)
        #self.voice_data.write(decoded)
        self.voice_data = decoded

    def read_voice_data(self) -> bytes:
        #self.voice_data.seek(0)
        #data = self.voice_data.read()
        #self.voice_data = io.BytesIO()
        data = self.voice_data
        self.voice_data = bytes()
        return data

    def handle_packet(self, packet: packets.ClientPacket) -> None:
        packet_type = type(packet)
        if packet_type not in self.packet_handlers:
            raise ValueError("Unknown packet type: %s" % (type(packet),))

        self.packet_handlers[packet_type](packet)

    def audio_levels_packet_handler(self, packet: packets.AudioLevelsPacket) -> None:
        self.player_id = packet.playerId
        for player_id, gain in zip(packet.playerIds, packet.gains):
            self.audio_levels_map[player_id] = gain

    def offsets_request_packet_handler(self, _: packets.OffsetsRequestPacket) -> None:
        self.send_data(packets.OffsetsResponsePacket(self.offsets))

    def volume_packet_handler(self, packet: packets.VolumePacket) -> None:
        self.volume = packet.volume