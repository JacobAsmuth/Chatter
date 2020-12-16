import shared
import client.memory as memory
import client.audio_engines.base as base
import numpy as np

class Linear(base.AudioEngineBase):
    def __init__(self):
        super(Linear, self).__init__()
        self.max_dist = 3

    def get_audio_levels(self, memory_read: memory.MemoryRead) -> shared.AudioLevelsPacket:
        if not memory_read.local_player:
            return shared.AudioLevelsPacket(playerIds=[], gains=[])
        player_ids = []
        gains = []
        lp_pos = memory_read.local_player.pos
        max_dist = self.max_dist

        for p in memory_read.players:
            dist = abs(np.linalg.norm(lp_pos - p.pos))
            gain = (1-(dist/max_dist)) * (dist < max_dist) # branchless. If dist >= max_dist, multiply by 0, otherwise keep the value.

            player_ids.append(p.playerId)
            gains.append(gain)

        return shared.AudioLevelsPacket(playerIds=player_ids, gains=gains)