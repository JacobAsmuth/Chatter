from typing import List
import numpy as np

import client.memory as memory
import client.audio_engines.base as base
import shared.packets as packets

class Exponential(base.AudioEngineBase):
    @staticmethod
    def get_audio_levels(memory_read: memory.MemoryRead, settings: packets.ServerSettingsPacket) -> tuple[List[int], List[int]]:
        lp = memory_read.local_player
        if lp is None:
            return [], []

        player_ids = []
        gains = []
        lp_dead = lp.dead
        lp_pos = lp.pos
        decay_constant = np.log(settings.lowest_hearable_volume) / (-settings.voice_distance)

        if memory_read.game_state == memory.GameState.DISCUSSION:
            for p in memory_read.players:
                gain = 1 * (lp_dead == p.dead)

                player_ids.append(p.playerId)
                gains.append(gain)
        else:
            for p in memory_read.players:
                dist = np.linalg.norm(lp_pos - p.pos)
                gain = (np.e ** (-dist*decay_constant)) * (dist < settings.voice_distance) * (lp_dead == p.dead) # branchless

                player_ids.append(p.playerId)
                gains.append(gain)

        return player_ids, gains