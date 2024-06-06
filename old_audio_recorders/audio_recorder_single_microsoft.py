"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains a script that acquires data from the microphone everytime the noise exceeds a rms threshold.
The audio is split each t seconds, and it is transcribed using microsoft APIs.
After s seconds of silence, the whole sentence is transcribed and sent to the client.
"""
import gc
import azure.cognitiveservices.speech as speechsdk
import threading
import pyaudio
import socket
import struct
import math
import wave
import time
import os
import argparse

language = "it-IT"
rms_threshold = 60
short_normalize = (1.0 / 32768.0)
chunk = 1024
audio_format = pyaudio.paInt16
channels = 1
rate = 44100
s_width = 2
split_silence_time = 0.5
final_silence_time = 1


class Recorder:
    def __init__(self, lang):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=audio_format, channels=channels, rate=rate, input=True, output=True,
                                  frames_per_buffer=chunk)
        self.prev_input = []
        self.max_chunks = 20
        self.string_to_send = ""
        self.speech_config = speechsdk.SpeechConfig(subscription=os.environ["COGNITIVE_SERVICE_KEY"], region="westeurope",
                                                    speech_recognition_language=lang)

    def microsoft_sender(self, wav_filename):
        audio_input = speechsdk.AudioConfig(filename=wav_filename)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, language=language,
                                                       audio_config=audio_input)
        result = speech_recognizer.recognize_once_async().get()
        del speech_recognizer
        return result

    def transcribe_file(self, wav_filename):
        result = self.microsoft_sender(wav_filename)
        print(result.text)
        if result.text:
            self.string_to_send = result.text
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

        start_time = time.time()
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
        end_time = time.time()
        wav_duration = end_time - start_time

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
            print("*** Waiting for the client to connect ***")
            connection, address = server_recorder_socket.accept()
            print("*** Waiting for client to be ready ***")
            connection.recv(1024).decode('utf-8')
            self.string_to_send = ""
            self.stream.start_stream()
            print("*** Listening ***")

            while True:
                current = time.time()
                end = time.time() + final_silence_time
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
                    client_msg = connection.recv(1024).decode('utf-8')
                    if client_msg == "":
                        print("*** Client disconnected from socket! ***")
                        break
                    # Empty the string in case a thread has written something in the meanwhile
                    self.string_to_send = ""
                    self.stream.start_stream()
                    print("*** Listening ***")


if __name__ == '__main__':
    # Define the program description
    text = 'This is the service for detecting noise and start recording.'
    # Initiate the parser with a description
    parser = argparse.ArgumentParser(description=text)
    # Add long and short argument
    parser.add_argument("--language", "-l", help="set the language of the audio recorder to en or it")
    # Read arguments from the command line
    args = parser.parse_args()
    if not args.language:
        print("No language provided. The default English language will be used.")
        language = "en-GB"
    else:
        if args.language == "it":
            language = "it-IT"
        else:
            language = "en-GB"
        print("The language of the audio recorder has been set to", language)

    # Create the socket - server side: waits for the client to connect
    server_recorder_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_recorder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_recorder_socket.bind(("0.0.0.0", 9090))
    server_recorder_socket.listen(1)

    a = Recorder(language)
    a.listen()
