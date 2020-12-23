from dataclasses import dataclass
from typing import List, Any

@dataclass
class ClientPacket:
    clientId: int

@dataclass
class ClientVoiceFramePacket(ClientPacket):
    frameId: float
    voiceFrame: bytes

@dataclass
class ServerVoiceFramePacket:
    frameId: float
    voiceFrame: bytes    

@dataclass
class AudioLevelsPacket(ClientPacket):
    playerName: str
    playerNames: List[str]
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

@dataclass
class ClientSettingsPacket:
    voice_distance: float = 3
    wall_attenuation: float = 1
    lowest_hearable_volume: float = 0.2

@dataclass
class ServerRestartingPacket:
    pass