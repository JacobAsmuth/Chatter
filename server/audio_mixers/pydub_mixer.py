from server.audio_mixers.base import AudioMixerBase
from server.client_object import ClientObject
import numpy as np
import pydub
 
class PydubMixer(AudioMixerBase):
    def mix(self, destination_client: ClientObject, all_voice_data: dict):
        final_audio: pydub.AudioSegment = None

        for source_client, source_audio in all_voice_data.items():
            if source_client is destination_client:
                continue

            gain = destination_client.audio_levels_map[source_client.player_id]
            gain = 0.5

            if gain > 0:
                if final_audio:
                    source_audio = source_audio.apply_gain(10*np.log10(gain))
                    final_audio = final_audio.overlay(source_audio)
                else:
                    final_audio = source_audio.apply_gain(10*np.log10(gain))
        if final_audio:
            return final_audio.raw_data
        return None