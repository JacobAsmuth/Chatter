import pickle
from dataclasses import dataclass
from typing import List
import sounddevice

VOICE_PORT = 5555
DATA_PORT = 6666
MAX_CONCURRENT_CONNECTIONS = 20
BYTES_PER_CHUNK = 1024

SAMPLE_WIDTH = 3  # Pydub specific value where '2' maps to 16 bits
SAMPLE_RATE = 48000
CHANNELS = 1

ENCODING = 'utf8'
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL

@dataclass
class UserInfoPacket:
    player_id: int

@dataclass
class PingPacket:
    pass

@dataclass
class ServerSettingsPacket:
    voice_distance: int
    wall_attenuation: int

@dataclass
class AudioLevelsPacket:
    player_ids: List[int]
    gains: List[float]