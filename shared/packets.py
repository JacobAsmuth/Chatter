from dataclasses import dataclass
from typing import List, Any

@dataclass
class ClientPacket:
    clientId: int

@dataclass
class ClientVoiceFramePacket(ClientPacket):
    frameId: int
    voiceData: bytes

@dataclass
class ServerVoiceFramePacket:
    frameId: int
    voiceData: bytes    

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
    voice_distance: int
    wall_attenuation: int