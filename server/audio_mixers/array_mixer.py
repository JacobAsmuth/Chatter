import audioop

from server.audio_mixers.base import AudioMixerBase
from server.client_object import ClientObject
from server.settings import Settings
import shared.consts as consts
 
class ArrayMixer(AudioMixerBase):
    # This function runs len(clients) * (1/consts.OUTPUT_BLOCK_TIME) times per second.
    @staticmethod
    def mix(destination_client: ClientObject, all_voice_frames: dict, settings: Settings):
        frames, gains = ArrayMixer.get_frames_and_gains(destination_client, all_voice_frames, settings)

        if len(frames) == 0:
            return None

        ratio = 1/len(frames)
        final_sample = None
        for sample, gain in zip(frames, gains):
            fragment = audioop.mul(sample, consts.BYTES_PER_SAMPLE, gain * ratio)
            if final_sample == None:
                final_sample = fragment
            else:
                delta = len(final_sample) - len(fragment)

                # Delta==0 is the 99.9999% case. Run it first to save a few checks.
                if delta == 0:
                    final_sample = audioop.add(final_sample, fragment, consts.BYTES_PER_SAMPLE)
                elif delta > 0:  # final sample bigger
                    final_sample = audioop.add(final_sample, fragment + bytes(delta), consts.BYTES_PER_SAMPLE)
                elif delta < 0:  # fragment bigger
                    final_sample = audioop.add(final_sample + bytes(-delta), fragment, consts.BYTES_PER_SAMPLE)
        
        return audioop.mul(final_sample, consts.BYTES_PER_SAMPLE, destination_client.volume * len(frames))

    @staticmethod
    def get_frames_and_gains(destination_client: ClientObject, all_voice_frames: dict, settings: Settings):
        frames = []
        gains = []
        ignore_client_gain = settings.ignore_client_gain
        audio_levels_map = destination_client.audio_levels_map
        for source_client, voice_frame in all_voice_frames.items():
            if source_client is destination_client:
                continue

            gain, _ = audio_levels_map[source_client.player_name]
            _, destination_can_hear_source = source_client.audio_levels_map[destination_client.player_name]
            gain = (ignore_client_gain + ((not ignore_client_gain) * gain)) * destination_can_hear_source

            if gain > 0:
                frames.append(voice_frame)
                gains.append(gain)

        return frames, gains