class JitterBuffer(object):
    def __init__(self, min_packets: int, max_packets: int) -> None:
        self.min_packets = min_packets
        self.max_packets = max_packets


    def get_packet(self) -> bytes:
        pass

    def add_packet(self, bytes) -> None:
        pass