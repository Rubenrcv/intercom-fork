'''Real-time Audio Intercommunicator.
'''

import argparse
import logging
import sounddevice as sd
import numpy as np
import socket
import time
import threading
import psutil

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

class Intercom_minimal:
    
    MAX_PAYLOAD_BYTES = 32768
    SAMPLE_TYPE = np.int16

    def __init__(self):
        ''' Set the sockets. '''
        self.sending_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiving_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listening_endpoint = ("0.0.0.0", args.listening_port)
        self.receiving_socket.bind(self.listening_endpoint)
        self.receiving_socket.settimeout(0)

    def pack_chunk(self, chunk):
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

    def send_packet(self, packet):
        ''' Sends an UDP packet.

        Parameters
        ----------

        packet : bytes

            A packet structure with the sequence of bytes to send.

        '''
        self.sending_socket.sendto(packet, (args.destination_address, args.destination_port))

    def receive_packet(self):
        ''' Receives an UDP packet without blocking.

        Returns
        -------

        bytes

           A packet.
        '''
        try:
            packet, sender = self.receiving_socket.recvfrom(self.MAX_PAYLOAD_BYTES)
            return packet
        except BlockingIOError:
            raise

    def unpack_packet(self, packet):
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
           
        chunk = np.frombuffer(packet, self.SAMPLE_TYPE)
        chunk = chunk.reshape(args.frames_per_chunk, args.number_of_channels)
        return chunk

    def record_io_and_play(self, indata, outdata, frames, time, status):
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
        packet = self.pack_chunk(indata)
        self.send_packet(packet)
        try:
            packet = self.receive_packet()
            chunk = self.unpack_packet(packet)
        except BlockingIOError:
            chunk = np.zeros((args.frames_per_chunk, args.number_of_channels), self.SAMPLE_TYPE)
        outdata[:] = chunk
        if __debug__:
            print(next(spinner), end='\b', flush=True)

    def run(self):
        '''Creates the stream, install the callback function, and waits for
        an enter-key pressing.'''
        with sd.Stream(device=(args.input_device, args.output_device),
                       dtype=self.SAMPLE_TYPE,
                       samplerate=args.frames_per_second,
                       blocksize=args.frames_per_chunk,
                       channels=args.number_of_channels,
                       callback=self.record_io_and_play):
            print("InterCom running ... press enter-key to quit")
            input()

class Intercom_minimal_debug(Intercom_minimal):

    def __init__(self):
        print("\nInterCom parameters:\n")
        print(args)
        super().__init__()
        print("\nUsing device:\n")
        print(sd.query_devices(args.input_device))
        self.CPU_total = 0
        self.CPU_samples = 0
        self.CPU_average = 0
        self.sent_bytes_counter = 0
        self.received_bytes_counter = 0
        self.sent_messages_counter = 0
        self.received_messages_counter = 0

    def send_packet(self, packet):
        super().send_packet(packet)
        self.sent_bytes_counter += len(packet)*np.dtype(self.SAMPLE_TYPE).itemsize*args.number_of_channels
        self.sent_messages_counter += 1

    def receive_packet(self):
        try:
            packet = super().receive_packet()
            self.received_bytes_counter += len(packet)
            self.received_messages_counter += 1
            return packet
        except BlockingIOError:
            raise

    def print_feedback(self):
        self.CPU_usage = psutil.cpu_percent()
        self.CPU_total += self.CPU_usage
        self.CPU_samples += 1
        self.CPU_average = self.CPU_total/self.CPU_samples
        elapsed_time = time.time() - self.old_time
        self.old_time = time.time()
        sent = int(self.sent_bytes_counter*8/1000/elapsed_time)
        received = int(self.received_bytes_counter*8/1000/elapsed_time)
        self.total_sent += sent
        self.total_received += received
        print(f"{self.sent_messages_counter:10d}{self.received_messages_counter:10d}{sent:10d}{received:10d}{self.total_sent:10d}{self.total_received:10d}{int(self.CPU_usage):5d}{int(self.CPU_average):5d}")
        self.sent_bytes_counter = 0
        self.received_bytes_counter = 0
        self.sent_messages_counter = 0
        self.received_messages_counter = 0
    
    def run(self):
        self.old_time = time.time()
        self.total_sent = 0
        self.total_received = 0
        print()
        print(f"{'':>10s}{'':>10s}{'':>10s}{'':>10s}{'total':>10s}{'total':>10s}");
        print(f"{'sent':>10s}{'received':>10s}{'sent':>10s}{'received':>10s}{'sent':>10s}{'received':>10s}{'':>5s}{'Avg.':>5s}");
        print(f"{'messages':>10s}{'messages':>10s}{'kbps':>10s}{'kbps':>10s}{'kbps':>10s}{'kbps':>10s}{'%CPU':>5s}{'%CPU':>5s}")
        print(f"{'='*70}")
        try:
            with sd.Stream(device=(args.input_device, args.output_device),
                       dtype=self.SAMPLE_TYPE,
                       samplerate=args.frames_per_second,
                       blocksize=args.frames_per_chunk,
                       channels=args.number_of_channels,
                       callback=self.record_io_and_play):
                while True:
                    self.print_feedback()
                    time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nIntercom_buffer: average CPU usage = {self.CPU_average} %")

if __name__ == "__main__":
    if __debug__:
        intercom = Intercom_minimal_debug()
    else:
        intercom = Intercom_minimal()
    try:
        intercom.run()
    except KeyboardInterrupt:
        parser.exit("\nInterrupted by user")
    except Exception as e:
        parser.exit(type(e).__name__ + ": " + str(e))
