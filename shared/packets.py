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
    canHearMe: List[bool]

@dataclass
class VolumePacket:
    volume: float

@dataclass
class OffsetsPacket:
    offsets: Any

@dataclass
class AllSettingsPacket:
    voice_distance: float = 3
    wall_attenuation: float = 1
    lowest_hearable_volume: float = 0.2
    haunting_ratio: float = 0.5
    imposter_voice_allowed: bool = True
    imposter_voice_during_discussion: bool = True

@dataclass
class SettingPacket:
    key: str
    value: Any

@dataclass
class ServerRestartingPacket:
    pass 