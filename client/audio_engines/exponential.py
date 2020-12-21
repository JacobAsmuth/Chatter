from typing import List

import client.memory as memory
import client.audio_engines.base as base
import numpy as np

class Exponential(base.AudioEngineBase):
    def __init__(self):
        super(Exponential, self).__init__()
        self.max_dist = 3
        self.lowest_hearable_volume = 0.2
        self.decay_constant = np.log(self.lowest_hearable_volume) / (-self.max_dist)

    def get_audio_levels(self, memory_read: memory.MemoryRead) -> tuple[List[int], List[int]]:
        if not memory_read.local_player:
            return [], []
        player_ids = []
        gains = []
        lp_pos = memory_read.local_player.pos
        decay_constant = self.decay_constant
        max_dist = self.max_dist

        for p in memory_read.players:
            dist = np.linalg.norm(lp_pos - p.pos)
            decay = np.e ** (-dist*decay_constant)
            
            gains.append(decay * (dist < max_dist))
            player_ids.append(p.playerId)

        return player_ids, gains