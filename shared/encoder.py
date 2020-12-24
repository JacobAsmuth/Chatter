from pyogg.opus_encoder import OpusEncoder
from pyogg.opus_decoder import OpusDecoder
import shared.consts as consts

class Encoder:
    def __init__(self) -> None:
        self._encoder = OpusEncoder()
        self._decoder = OpusDecoder()

        self._encoder.set_channels(consts.CHANNELS)
        self._encoder.set_sampling_frequency(consts.SAMPLE_RATE)
        self._encoder.set_application('voip')


        self._decoder.set_channels(consts.CHANNELS)
        self._decoder.set_sampling_frequency(consts.SAMPLE_RATE)


    def decode(self, frame: bytes) -> bytes:
        return self._decoder.decode(frame)

    def encode(self, frame: bytes) -> bytes:
        return self._encoder.encode(frame).tobytes()