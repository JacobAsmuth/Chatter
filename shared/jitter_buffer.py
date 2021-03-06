from collections import deque
from typing import Union
from dataclasses import dataclass

@dataclass
class Frame:
    frameId: float
    samples: bytes

class JitterBuffer(object):
    def __init__(self, min_frame_count: int, max_frame_count: int) -> None:
        self.min_frame_count = min_frame_count
        self.max_frame_count = max_frame_count
        self.last_frame_time = None

        self.frames = deque()

    def get_samples(self) -> Union[bytes, None]:
        if len(self.frames) < self.min_frame_count:
            return None

        frame = self.frames.popleft()
        return frame.samples

    def add_frame(self, frame_id: float, samples: bytes) -> None:
        insert_index = len(self.frames)

        if insert_index == self.max_frame_count:
            self.frames.popleft()
            insert_index -= 1

        for i, frame in enumerate(self.frames):
            if frame_id < frame.frameId:
                insert_index = i
                break

        self.frames.insert(insert_index, Frame(frame_id, samples))
        