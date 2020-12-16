import audioop

from server.audio_mixers.base import AudioMixerBase
from server.client_object import ClientObject
import shared
 
class ArrayMixer(AudioMixerBase):
    def mix(self, destination_client: ClientObject, all_voice_data: dict):
        samples = []
        sample_gains = []

        for source_client, source_audio in all_voice_data.items():
            if source_client is destination_client:
                continue

            gain = destination_client.audio_levels_map[source_client.player_id]

            if gain > 0:
                samples.append(source_audio.raw_data)
                sample_gains.append(gain)

        if len(samples) == 0:
            return None

        ratio = 1/len(samples)
        final_sample = None
        for sample, gain in zip(samples, sample_gains):
            fragment = audioop.mul(sample, shared.SAMPLE_WIDTH, gain * ratio)
            if final_sample == None:
                final_sample = fragment
            else:
                final_sample_len = len(final_sample)
                fragment_len = len(fragment)
                delta = final_sample_len - fragment_len
                if delta > 0:  # final sample bigger
                    fragment += bytes(0 for _ in range(delta))
                elif delta < 0:  # fragment bigger
                    final_sample += bytes(0 for _ in range(-delta))
                final_sample = audioop.add(final_sample, fragment, shared.SAMPLE_WIDTH)
        

        return audioop.mul(final_sample, shared.SAMPLE_WIDTH, destination_client.volume)