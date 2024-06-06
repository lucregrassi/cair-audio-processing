"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains a script that acquires data from the microphone everytime the noise exceeds a rms threshold.
The audio is split each t seconds, and it is transcribed using google APIs.
Once a passphrase is recognized the whole text is transcribed and sent to the client.
"""
from google.cloud import speech
import threading
import pyaudio
import socket
import struct
import math
import wave
import time
import gc
import os
import io

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "caresses-nlp-3b12fdd574b1.json"

# Alternative way
# SUBSCRIPTION_KEY = ""

rms_threshold = 60
short_normalize = (1.0 / 32768.0)
chunk = 1024
audio_format = pyaudio.paInt16
channels = 1
rate = 44100
s_width = 2
split_silence_time = 0.5
final_silence_time = 1
exit_keywords = ["passo e chiudo", "cosa ne pensi"]

# Create the socket - server side: waits for the client to connect
server_recorder_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_recorder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_recorder_socket.bind(("0.0.0.0", 9090))
server_recorder_socket.listen(1)


def google_sender(speech_file):
    client = speech.SpeechClient()

    with io.open(speech_file, "rb") as audio_file:
        content = audio_file.read()

    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="it-IT",
    )

    response = client.recognize(config=config, audio=audio)

    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    for result in response.results:
        # The first alternative is the most likely one for this portion.
        return result.alternatives[0].transcript


class Recorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=audio_format, channels=channels, rate=rate, input=True, output=True,
                                  frames_per_buffer=chunk)
        self.prev_input = []
        self.max_chunks = 20
        self.string_to_send = ""

    def transcribe_file(self, wav_filename):
        result = google_sender(wav_filename)
        print(result)
        if result:
            self.string_to_send = self.string_to_send + " " + result
        else:
            print("*** Not able to perform speech to text ***")
        gc.collect()
        # Delete the original wav file without final silence
        if os.path.exists(wav_filename):
            os.remove(wav_filename)

    @staticmethod
    def rms(frame):
        count = len(frame) / s_width
        frmt = "%dh" % count
        shorts = struct.unpack(frmt, frame)

        sum_squares = 0.0
        for sample in shorts:
            n = sample * short_normalize
            sum_squares += n * n
        rms = math.pow(sum_squares / count, 0.5)
        return rms * 1000

    def record(self):
        print('*** Noise detected: start recording ***')
        rec = []
        if self.prev_input:
            for c in self.prev_input:
                rec.append(c)

        current = time.time()
        end = time.time() + split_silence_time
        timeout = time.time() + 30
        while current <= end:
            data = self.stream.read(chunk)
            if self.rms(data) >= rms_threshold:
                end = time.time() + split_silence_time
            current = time.time()
            rec.append(data)
            # Limit the audio duration to 1 minute
            if time.time() > timeout:
                print("Audio reached 30 seconds - stop recording")
                break
        self.prev_input = []
        self.write(b''.join(rec))

    def write(self, recording):
        date_time = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(os.getcwd(), '{}.wav'.format(date_time))
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(self.p.get_sample_size(audio_format))
        wf.setframerate(rate)
        wf.writeframes(recording)
        wf.close()
        # print('Written to file: {}'.format(filename))
        t1 = threading.Thread(target=self.transcribe_file, args=(format(filename),))
        t1.start()
        print('*** Recording saved. Return to listening ***')

    def listen(self):
        while True:
            print("*** Waiting for client to connect ***")
            connection, address = server_recorder_socket.accept()
            print("*** Waiting for client to be ready ***")
            connection.recv(1024).decode('utf-8')
            self.stream.start_stream()
            print("*** Listening ***")
            sentence_type = ""

            while True:
                current = time.time()
                end = time.time() + final_silence_time
                if sentence_type == "w":
                    while True:
                        if any(elem in self.string_to_send.lower() for elem in exit_keywords):
                            break
                        audio_input = self.stream.read(chunk, exception_on_overflow=False)
                        rms_val = self.rms(audio_input)
                        if rms_val > rms_threshold:
                            self.record()
                        else:
                            self.prev_input.append(audio_input)
                            if len(self.prev_input) > self.max_chunks:
                                self.prev_input = self.prev_input[1:]
                else:
                    while current <= end:
                        audio_input = self.stream.read(chunk, exception_on_overflow=False)
                        rms_val = self.rms(audio_input)
                        if rms_val > rms_threshold:
                            end = time.time() + final_silence_time
                            self.record()
                        else:
                            self.prev_input.append(audio_input)
                            if len(self.prev_input) > self.max_chunks:
                                self.prev_input = self.prev_input[1:]
                            current = time.time()
                if self.string_to_send:
                    self.stream.stop_stream()
                    self.string_to_send = self.string_to_send.strip()
                    print("*** Sending to client:", self.string_to_send)
                    # Useless to surround with a try - except because send does not care
                    connection.send(self.string_to_send.encode('utf-8'))
                    print("*** Waiting for client to be ready ***")
                    sentence_type = connection.recv(1024).decode('utf-8')
                    if sentence_type == "":
                        print("*** Client disconnected from socket! ***")
                        break
                    # Empty the string in case a thread has written something in the meanwhile
                    self.string_to_send = ""
                    self.stream.start_stream()
                    print("*** Listening ***")


a = Recorder()
a.listen()
