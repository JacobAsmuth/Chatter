import abc

import shared
import client.memory as memory

class AudioEngineBase(abc.ABC):
    @abc.abstractmethod
    def get_audio_levels(self, memory_read: memory.MemoryRead) -> shared.AudioLevelsPacket: ...