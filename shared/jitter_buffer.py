from collections import deque
from typing import Union
from dataclasses import dataclass

@dataclass
class Frame:
    frameId: int
    samples: bytes

class JitterBuffer(object):
    def __init__(self, min_frame_count: int, max_frame_count: int) -> None:
        self.min_frame_count = min_frame_count
        self.max_frame_count = max_frame_count
        self.expected_next_frame_id = 0

        self.frames = deque()

    def get_samples(self) -> Union[bytes, None]:
        if len(self.frames) < self.min_frame_count:
            return None

        while self.frames[0].frameId < self.expected_next_frame_id:
            self.frames.popleft()
            
        if self.frames[0].frameId == self.expected_next_frame_id:
            frame = self.frames.popleft()
            self.expected_next_frame_id += 1
            return frame.samples

        if self.frames[0].frameId > self.expected_next_frame_id:
            self.expected_next_frame_id += 1
            return None

    def add_frame(self, frame_id: int, samples: bytes) -> None:
        if frame_id < self.expected_next_frame_id:
            return

        if frame_id == self.expected_next_frame_id:
            self.frames.insert(0, Frame(frame_id, samples))
            return

        insert_index = len(self.frames)

        if insert_index == self.max_frame_count:
            self.frames.popleft()
            insert_index -= 1

        for i, frame in enumerate(self.frames):
            if frame_id < frame.frameId:
                insert_index = i
                break

        self.frames.insert(insert_index, Frame(frame_id, samples))
        