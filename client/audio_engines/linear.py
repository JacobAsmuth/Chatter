import shared
from typing import List
import client.memory as memory
import client.audio_engines.base as base

class Linear(base.AudioEngineBase):
    def __init__(self):
        super(Linear, self).__init__()

    def get_audio_levels(self, memory_read: memory.MemoryRead) -> shared.AudioLevelsPacket:
        return shared.AudioLevelsPacket()