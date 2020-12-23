from typing import List
import numpy as np

import client.memory as memory
import client.audio_engines.base as base
import shared.packets as packets


class Linear(base.AudioEngineBase):
    @staticmethod
    def get_audio_levels(memory_read: memory.MemoryRead, settings: packets.ServerSettingsPacket) -> tuple[List[int], List[int]]:
        lp = memory_read.local_player
        if lp is None:
            return [], []

        player_ids = []
        gains = []
        lp_pos = lp.pos
        lp_dead = lp.dead
        max_dist = settings.voice_distance

        if memory_read.game_state == memory.GameState.DISCUSSION:
            for p in memory_read.players:
                gain = 1 * (lp_dead == p.dead)

                player_ids.append(p.playerId)
                gains.append(gain)
        else:
            for p in memory_read.players:
                dist = abs(np.linalg.norm(lp_pos - p.pos))
                gain = (1-(dist/max_dist)) * (dist < max_dist) * (lp_dead == p.dead) # branchless

                player_ids.append(p.playerId)
                gains.append(gain)

        return player_ids, gains