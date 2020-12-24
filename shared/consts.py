import socket
import pickle

SERVER_AWS_IP = "50.18.150.140"

VOICE_PORT = 5555
DATA_PORT = VOICE_PORT + 1
MAX_CONCURRENT_CONNECTIONS = 20
SOCKET_TYPE = socket.SOCK_DGRAM

SAMPLE_RATE = 16000
OUTPUT_BLOCK_TIME = 0.02
SAMPLES_PER_FRAME = int(SAMPLE_RATE*OUTPUT_BLOCK_TIME)
BYTES_PER_SAMPLE = 2
CHANNELS = 1
BYTES_PER_CHUNK = SAMPLES_PER_FRAME * BYTES_PER_SAMPLE * CHANNELS

ENCODING = 'utf8'
PICKLE_PROTOCOL = pickle.HIGHEST_PROTOCOL
CLEANUP_TIMEOUT = 1
PACKET_SIZE: int = 2**15

# number of frames to store in the jitter buffers
MIN_BUFFER_SIZE = 5
MAX_BUFFER_SIZE = 10

GIT_UPDATE_CHECK_FREQUENCY = 10  # seconds

SERVER_SETTINGS_FILE = 'settings.pkl'

ACK_MSG = bytes([0])