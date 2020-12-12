import shared
from typing import List
import client.memory as memory
import client.audio_engines.base as base

class Linear(base.AudioEngineBase):
    def __init__(self):
        super(Linear, self).__init__()

    def dist(self, p1, p2):
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def get_audio_levels(self, memory_read: memory.MemoryRead) -> shared.AudioLevelsPacket:
        player_ids = []
        gains = []
        lp_coord = memory_read.local_player.pos
        for p in memory_read.players:
            if self.dist(lp_coord, p.pos) < 7:
                player_ids.append(p.playerId)
                gains.append(1)
            else:
                player_ids.append(p.playerId)
                gains.append(0)

        return shared.AudioLevelsPacket(playerIds=player_ids, gains=gains)