import shared
from typing import List
import client.memory as memory

class Linear:
    def get_audio_levels(self, memory_read: memory.MemoryRead) -> shared.AudioLevelsPacket:
        return shared.AudioLevelsPacket()