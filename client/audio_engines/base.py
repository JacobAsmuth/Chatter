import abc
from typing import List

import client.memory as memory
import shared.packets as packets

class AudioEngineBase(abc.ABC):
    @abc.abstractstaticmethod
    def get_audio_levels(memory_read: memory.MemoryRead, settings: packets.ServerSettingsPacket) -> tuple[List[int], List[int]]: ...