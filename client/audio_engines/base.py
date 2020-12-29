import abc
from typing import List

import client.memory as memory
import shared.packets as packets

class AudioEngineBase(abc.ABC):
    @abc.abstractmethod
    def calculate_falloff(self, local_player: memory.Player, other_player: memory.Player, settings: packets.ClientSettingsPacket) -> float: ...

    def get_audio_levels(self, memory_read: memory.MemoryRead, settings: packets.ClientSettingsPacket, imposter_voice: bool) -> tuple[List[str], List[float], List[bool]]:
        lp = memory_read.local_player
        if lp is None:
            return [], [], []

        player_names = []
        gains = []
        canHearMe = []
        lp_dead = lp.dead
        lp_in_vent = lp.inVent
        haunting_ratio = settings.haunting_ratio
        lp_is_imposter = lp.impostor

        if memory_read.game_state == memory.GameState.DISCUSSION:
            for p in memory_read.players:
                gain = lp_dead + ((not lp_dead) * (not p.dead))  # dead players hear all, alive players only hear other alive players

                player_names.append(p.name)
                gains.append(gain)
                canHearMe.append((not imposter_voice) or (imposter_voice and p.impostor))
        else:
            for p in memory_read.players:
                gain = self.calculate_falloff(lp, p, settings)
                both_in_vent = lp_in_vent and p.inVent
                gain = both_in_vent + ((not both_in_vent) * gain) # 1 if both in vent, 'gain' otherwise

                hauntable = lp_is_imposter and p.dead and haunting_ratio > 0
                
                # If hauntable, then gain = gain * haunting ratio
                # If not hauntable, then gain = gain
                gain = (hauntable * gain * haunting_ratio) + ((not hauntable) * gain)

                player_names.append(p.name)
                gains.append(gain)
                canHearMe((not imposter_voice) or (imposter_voice and p.impostor))

        return player_names, gains, canHearMe