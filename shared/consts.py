import socket
import pickle

VOICE_PORT = 5555
DATA_PORT = VOICE_PORT + 1
MAX_CONCURRENT_CONNECTIONS = 20
SOCKET_TYPE = socket.SOCK_DGRAM

SAMPLE_RATE = 16000
OUTPUT_BLOCK_TIME = 0.05
SAMPLES_PER_CHUNK = int(SAMPLE_RATE*OUTPUT_BLOCK_TIME)
BYTES_PER_SAMPLE = 2
CHANNELS = 1
BYTES_PER_CHUNK = SAMPLES_PER_CHUNK * BYTES_PER_SAMPLE * CHANNELS

ENCODING = 'utf8'
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL
CLEANUP_TIMEOUT = 1
PACKET_SIZE = 2**11