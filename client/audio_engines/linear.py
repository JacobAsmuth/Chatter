from typing import List
import numpy as np

import client.memory as memory
import client.audio_engines.base as base
import shared.packets as packets


class Linear(base.AudioEngineBase):
    def calculate_falloff(self, local_player: memory.Player, other_player: memory.Player, settings: packets.ClientSettingsPacket) -> float:
        dist = abs(np.linalg.norm(local_player.pos - other_player.pos))
        return (1-(dist/settings.voice_distance)) * (dist < settings.voice_distance) # branchless hype