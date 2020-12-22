import audioop

from server.audio_mixers.base import AudioMixerBase
from server.client_object import ClientObject
import shared.consts as consts
 
class ArrayMixer(AudioMixerBase):
    # This function runs len(clients) * 20 times per second. Efficiency is key. 
    def mix(_, destination_client: ClientObject, all_voice_frames: dict):
        frames = []
        sample_gains = []

        for source_client, voice_frame in all_voice_frames.items():
            if source_client is destination_client:
                continue

            #gain = destination_client.audio_levels_map[source_client.player_id]
            gain = 1

            if gain > 0:
                frames.append(voice_frame)
                sample_gains.append(gain)

        if len(frames) == 0:
            return None

        ratio = 1/len(frames)
        final_sample = None
        for sample, gain in zip(frames, sample_gains):
            fragment = audioop.mul(sample, consts.BYTES_PER_SAMPLE, gain * ratio)
            if final_sample == None:
                final_sample = fragment
            else:
                delta = len(final_sample) - len(fragment)

                # Delta==0 is the 99.9999% case. Run it first to save a few checks.
                if delta == 0:
                    final_sample = audioop.add(final_sample, fragment, consts.BYTES_PER_SAMPLE)
                if delta > 0:  # final sample bigger
                    final_sample = audioop.add(final_sample, fragment + bytes(0 for _ in range(delta)), consts.BYTES_PER_SAMPLE)
                elif delta < 0:  # fragment bigger
                    final_sample = audioop.add(final_sample + bytes(0 for _ in range(-delta)), fragment, consts.BYTES_PER_SAMPLE)
        
        return audioop.mul(final_sample, consts.BYTES_PER_SAMPLE, destination_client.volume)