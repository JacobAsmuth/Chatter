import abc
from typing import List

import shared
import client.memory as memory

class AudioEngineBase(abc.ABC):
    @abc.abstractmethod
    def get_audio_levels(self, players: List[memory.Player]) -> shared.AudioLevelsPacket:
        pass