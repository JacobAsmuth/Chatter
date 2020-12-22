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
    playerId: int
    playerIds: List[int]
    gains: List[float]

@dataclass
class VolumePacket(ClientPacket):
    volume: float

@dataclass
class OffsetsRequestPacket(ClientPacket):
    pass

@dataclass
class OffsetsResponsePacket:
    offsets: Any

@dataclass
class ServerSettingsPacket:
    voice_distance: float
    wall_attenuation: float
    lowest_hearable_volume: float