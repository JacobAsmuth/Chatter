import pickle
from dataclasses import dataclass
from typing import List, Any

VOICE_PORT = 5555
DATA_PORT = 6666
MAX_CONCURRENT_CONNECTIONS = 20
SAMPLES_PER_CHUNK = 1024

SAMPLE_WIDTH = 2  # Pydub specific value where '2' maps to 16 bits
SAMPLE_RATE = 44100
CHANNELS = 2
BYTES_PER_CHUNK = SAMPLES_PER_CHUNK * SAMPLE_WIDTH * CHANNELS

ENCODING = 'utf8'
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

@dataclass
class UserInfoPacket:
    playerId: int

@dataclass
class PingPacket:
    pass

@dataclass
class ServerSettingsPacket:
    voice_distance: int
    wall_attenuation: int

@dataclass
class AudioLevelsPacket:
    playerIds: List[int]
    gains: List[float]

@dataclass
class VolumePacket:
    volume: float

@dataclass
class OffsetsRequestPacket:
    pass

@dataclass
class OffsetsResponsePacket:
    offsets: Any