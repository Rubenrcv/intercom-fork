import argparse
import logging

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('-i', '--input-device', type=int_or_str,
                    help='input device ID or substring')
parser.add_argument('-o', '--output-device', type=int_or_str,
                    help='output device ID or substring')
parser.add_argument('-c', '--channels', type=int, default=2,
                    help='number of channels')
parser.add_argument('-t', '--dtype', help='audio data type')
parser.add_argument('-s', '--samplerate', type=float, help='sampling rate')
parser.add_argument('-b', '--blocksize', type=int, help='block size')
parser.add_argument('-l', '--latency', type=float, help='latency in seconds')
parser.add_argument('-a', '--destination_address', type=int_or_str, default="localhost", help='destination address')
parser.add_argument('-p', '--destination_port', type=int, default=4000, help='destination port')
args = parser.parse_args()

try:
    import sounddevice as sd
    import numpy as np # Make sure NumPy is loaded before it is used in the callback
    import socket

    sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listening_endpoint = ("0.0.0.0", 4444)
    receiving_socket.bind(listening_endpoint)
    receiving_socket.settimeout(0)

    def send(chunk):
        sending_socket.sendto(chunk, (args.destination_address, args.destination_port))

    def receive():
        try:
            chunk, sender = receiving_socket.recvfrom(32768)
            return chunk
        except BlockingIOError:
            return np.zeros((args.blocksize, args.channels), args.dtype)

    def callback(indata, outdata, frames, time, status):
        send(indata)
        chunk = receive()
        outdata[:] = chunk
        print(".", end='', flush=True)

    with sd.Stream(device=(args.input_device, args.output_device),
                   samplerate=args.samplerate, blocksize=args.blocksize,
                   dtype=args.dtype, latency=args.latency,
                   channels=args.channels, callback=callback):
        print('#' * 80)
        print('press Return to quit')
        print('#' * 80)
        input()
except KeyboardInterrupt:
    parser.exit('\nInterrupted by user')
except Exception as e:
    parser.exit(type(e).__name__ + ': ' + str(e))
