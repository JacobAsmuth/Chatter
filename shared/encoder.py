from pyogg import OpusEncoder, OpusDecoder
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
        try:
            return frame
            return self._decoder.decode(bytearray(frame))
        except Exception as e:
            print("Decode error: ", str(e))

    def encode(self, frame: bytes) -> bytes:
        try:
            return frame
            return self._encoder.encode(frame).tobytes()
        except Exception as e:
            print("Encode error: ", str(e))
