import shared
import threading
import queue
import socket
import collections
import pickle
import time

class ClientObject:
    def __init__(self, voice_socket: socket.socket, user_id: str):
        self.user_id = user_id
        self.voice_socket = voice_socket

        self.closing = False
        self.player_id = None  # In-game player ID
        self.data_socket = None
        self.send_queue = queue.Queue()
        self.audio_levels_map = collections.defaultdict(float)
        self.packet_handlers = {
            shared.PingPacket: self.ping_packet_handler,
            shared.UserInfoPacket: self.user_info_packet_handler,
            shared.AudioLevelsPacket: self.audio_levels_packet_handler,
        }

    def close(self):
        self.closing = True

        while not self.send_queue.empty():
            self.send_queue.get()

        self.voice_socket.close()
        if self.data_socket:
            self.data_socket.close()

    def set_data_socket(self, data_socket: socket.socket):
        self.data_socket = data_socket
        threading.Thread(target=self.receive_data_from_client, daemon=True).start()
        threading.Thread(target=self.send_data_to_client, daemon=True).start()

    def send_data_to_client(self):
        while True:
            try:
                object_to_send = self.send_queue.get_nowait()
                val = pickle.dumps(object_to_send, protocol=shared.PICKLE_PROTOCOL)
                self.data_socket.sendall(val)
            except queue.Empty:
                time.sleep(0.1)
            except Exception as e:
                if not self.closing:
                    print("Unable to send %s: %s" % (object_to_send, e))
                else:
                    break

    def send(self, packet):
        self.send_queue.put_nowait(packet)

    def receive_data_from_client(self):
        while True:
            try:
                packet = pickle.loads(self.data_socket.recv(1024))
                packet_type = type(packet)
                if packet_type in self.packet_handlers:
                    self.packet_handlers[packet_type](packet)
                else:
                    print("Unkown packet: %s" % (packet,))
            except WindowsError as e:
                if not self.closing:
                    print("Error parsing packet: %s, closing socket" % (e,))
                    self.data_socket.close()
                break
            except Exception as e:
                print("Error parsing packet: %s" % (e,))

    def ping_packet_handler(self, packet):
        print("Ping from %s received!" % (self.user_id,))

    def user_info_packet_handler(self, packet: shared.UserInfoPacket):
        self.player_id = packet.player_id

    def audio_levels_packet_handler(self, packet: shared.AudioLevelsPacket):
        for player_id, gain in zip(packet.player_ids, packet.gains):
            self.audio_levels_map[player_id] = gain