import abc
from typing import List

import client.memory as memory

class AudioEngineBase(abc.ABC):
    @abc.abstractmethod
    def get_audio_levels(self, memory_read: memory.MemoryRead) -> tuple[List[int], List[int]]: ...