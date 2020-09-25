'''Real-time Audio Intercommunicator.
'''
import argparse
import logging

def spinning_cursor():
    ''' https://stackoverflow.com/questions/4995733/how-to-create-a-spinning-command-line-cursor
    '''
    while True:
        for cursor in '|/-\\':
            yield cursor
spinner = spinning_cursor()

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

    def pack_chunk(chunk):
        ''' Builds a packet with a chunk.

        Parameters
        ----------

        chunk : numpy.ndarray

            A chunk of audio.

        Returns
        -------

        bytes

            A packet.
        '''
        return chunk

    def send_packet(packet):
        ''' Sends an UDP packet.

        Parameters
        ----------

        packet : bytes

            A packet structure with the sequence of bytes to send.

        '''
        sending_socket.sendto(packet, (args.destination_address, args.destination_port))

    def receive_packet():
        ''' Receives an UDP packet without blocking.

        Returns
        -------

        bytes

           A packet.
        '''
        try:
            packet, sender = receiving_socket.recvfrom(MAX_PAYLOAD_BYTES)
            return packet
        except BlockingIOError:
            raise

    def unpack_packet(packet):
        ''' Unpack a packet.

        Parameters
        ----------

        packet : bytes

            A packet.

        Returns
        -------

        numpy.ndarray

            A chunk.
        '''
           
        chunk = np.frombuffer(packet, SAMPLE_TYPE)
        chunk = chunk.reshape(args.frames_per_chunk, args.number_of_channels)
        return chunk

    def record_io_and_play(indata, outdata, frames, time, status):
        '''Interruption handler that samples a chunk, builds a packet with the
        chunk, sends the packet, receives a packet, unpacks it to get
        a chunk, and plays the chunk.

        Parameters
        ----------

        indata : numpy.ndarray

            The chunk of audio with the recorded data.

        outdata : numpy.ndarray

            The chunk of audio with the data to play.

        frames : int16

            The number of frames in indata and outdata.

        time : CData

            Time-stamps of the first frame in indata, in outdata (that
            is time at which the callback function was called.

        status : CallbackFlags

            Indicates if underflow or overflow conditions happened
            during the last call to the callbak function.

        '''
        packet = pack_chunk(indata)
        send_packet(packet)
        try:
            packet = receive_packet()
            chunk = unpack_packet(packet)
        except BlockingIOError:
            chunk = np.zeros((args.frames_per_chunk, args.number_of_channels), SAMPLE_TYPE)
        outdata[:] = chunk
        print(next(spinner), end='\b', flush=True)

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
