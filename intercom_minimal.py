'''Real-time Audio Intercommunicator.
'''
import argparse
import logging

def int_or_str(text):
    '''Helper function for argument parsing.
    '''
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-i", "--input-device", type=int_or_str,
                    help="Input device ID or substring")
parser.add_argument("-o", "--output-device", type=int_or_str,
                    help="Output device ID or substring")
parser.add_argument("-c", "--number_of_channels", type=int, default=2,
                    help="Number of number_of_channels")
parser.add_argument("-s", "--frames_per_second", type=float,
                    default=44100, help="sampling rate in frames/second")
parser.add_argument("-f", "--frames_per_chunk", type=int,
                    default=1024, help="Number of frames in a chunk")
parser.add_argument("-l", "--listening_port", type=int,
                    default=4444, help="My listening port")
parser.add_argument("-a", "--destination_address", type=int_or_str,
                    default="localhost",
                    help="Destination (interlocutor's listening-) address")
parser.add_argument("-p", "--destination_port", type=int,
                    default=4444,
                    help="Destination (interlocutor's listing-) port")
args = parser.parse_args()

try:
    import sounddevice as sd
    import numpy as np
    import socket

    MAX_PAYLOAD_BYTES = 32768
    SAMPLE_TYPE = np.int16

    print("Using device:")
    print(sd.query_devices(args.input_device))
    
    sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listening_endpoint = ("0.0.0.0", args.listening_port)
    receiving_socket.bind(listening_endpoint)
    receiving_socket.settimeout(0)

    def send(chunk):
        sending_socket.sendto(chunk, (args.destination_address, args.destination_port))

    def receive():
        try:
            chunk, sender = receiving_socket.recvfrom(MAX_PAYLOAD_BYTES)
            chunk = np.frombuffer(chunk, SAMPLE_TYPE)
            chunk = chunk.reshape(args.frames_per_chunk, args.number_of_channels)
            return chunk
        except BlockingIOError:
            return np.zeros((args.frames_per_chunk, args.number_of_channels), SAMPLE_TYPE)

    def record_io_and_play(indata, outdata, frames, time, status):
        send(indata)
        chunk = receive()
        outdata[:] = chunk
        print(".", end='', flush=True)

    with sd.Stream(device=(args.input_device, args.output_device),
                   dtype=SAMPLE_TYPE,
                   samplerate=args.frames_per_second,
                   blocksize=args.frames_per_chunk,
                   channels=args.number_of_channels,
                   callback=record_io_and_play):
        print('#' * 80)
        print("press Return to quit")
        print('#' * 80)
        input()
except KeyboardInterrupt:
    parser.exit("\nInterrupted by user")
except Exception as e:
    parser.exit(type(e).__name__ + ": " + str(e))
