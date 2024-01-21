"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains the Recorder class that acquires data from the microphone everytime the noise exceeds a rms threshold.
The audio is split each t seconds, and it is transcribed using microsoft APIs.
Once a t second silence has elapsed or a passphrase is recognized the whole text is transcribed,
tagged and sent to the client.
The class also gives the possibility of performing just a single recognition and returns the result.
"""
from cairlib.DialogueTurn import DialogueTurn, TurnPiece
from speaker_recognition_util import identify_speaker
from datetime import datetime
import azure.cognitiveservices.speech as speechsdk
import xml.etree.cElementTree as ET
import threading
import pyaudio
import struct
import math
import wave
import string
import time
import json
import os
import gc

rms_threshold = 40
short_normalize = (1.0 / 32768.0)
chunk = 1024
audio_format = pyaudio.paInt16
channels = 1
rate = 44100
s_width = 2
split_silence_time = 0.5
final_silence_time = 2
exit_keywords = ["passo e chiudo", "cosa ne pensi"]

log_filename = "logs/microphone_log_controlled_neutral_tone.txt"
file_lock = threading.Lock()


class Recorder:
    def __init__(self, lang):
        self.p = pyaudio.PyAudio()
        info = self.p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        input_device = -1
        for i in range(0, num_devices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print(self.p.get_device_info_by_host_api_device_index(0, i).get('name'))
                if "USB PnP Audio Device" in self.p.get_device_info_by_host_api_device_index(0, i).get('name'):
                    input_device = i
        if input_device == -1:
            print("Using default microphone")
            self.stream = self.p.open(format=audio_format, channels=channels, rate=rate, input=True, output=True,
                                      frames_per_buffer=chunk, start=False)
        else:
            print("Using USB PnP Audio Device")
            self.stream = self.p.open(format=audio_format, channels=channels, rate=rate, input=True, output=True,
                                      frames_per_buffer=chunk, start=False, input_device_index=input_device)

        self.prev_input = []
        self.max_chunks = 20
        # Initialize object that will contain the data related to the dialogue turn
        self.dialogue_turn = DialogueTurn()
        self.recognized_text = ""
        self.mode = "continuous"
        self.root = ET.Element("response")
        self.speech_config = speechsdk.SpeechConfig(subscription=os.environ["COGNITIVE_SERVICE_KEY"],
                                                    region="westeurope", speech_recognition_language=lang)
        self.t1 = threading.Thread(target=self.speech_and_speaker_recognition, args=("", 0,))
        self.log = open(log_filename, "a+")
        self.speaker_reco_start_time = 0
        self.speaker_reco_end_time = 0

    def speaker_recognition(self, wav_filename, prof_dict, ident_spk):
        prof_ids = ','.join(prof_dict.keys())
        print("T2: Trying to identify speaker...")
        self.speaker_reco_start_time = time.time()
        ident_speaker_id, confidence = identify_speaker(prof_ids, wav_filename)
        self.speaker_reco_end_time = time.time()
        if confidence > 0.3:
            ident_spk[0] = ident_speaker_id
            speaker_name = prof_dict[ident_speaker_id]
            print("T2: Identified speaker:", speaker_name)
            print("T2: Confidence:", confidence)
        else:
            print("T2: No speaker identified")

    def speech_recognition(self, wav_filename):
        print("T1: Performing speech to text...")
        audio_input = speechsdk.AudioConfig(filename=wav_filename)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_input)
        start_time = time.time()
        result = speech_recognizer.recognize_once_async().get()
        end_time = time.time()
        # If something has been recognized by Microsoft
        if result.text:
            with file_lock:
                self.log.write("speech_to_text_time:" + str(end_time - start_time) + "\n")
            sentence = result.text.translate(str.maketrans('', '', string.punctuation)).lower()
            if len(sentence) > 512:
                print("STT string exceeds 512 characters - truncated")
                sentence = sentence[:512]
            # Add a turn piece only if the user said something more than the phrase to end the turn
            if sentence:
                self.recognized_text = self.recognized_text + " " + sentence
        else:
            print("T1: Not able to perform speech to text!")
        del speech_recognizer
        gc.collect()
        # Delete the original wav file without final silence
        if os.path.exists(wav_filename):
            os.remove(wav_filename)

    def speech_and_speaker_recognition(self, wav_filename, wav_duration):
        if os.path.isfile("profiles.json"):
            with open('profiles.json', 'r', encoding='utf-8') as f:
                prof_dict = json.load(f)
        else:
            prof_dict = {}
        ident_speaker_id = ["00000000-0000-0000-0000-000000000000"]
        t2 = threading.Thread(target=self.speaker_recognition, args=(format(wav_filename), prof_dict, ident_speaker_id))
        if prof_dict:
            t2.start()
        print("T1: Performing speech to text...")
        audio_input = speechsdk.AudioConfig(filename=wav_filename)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_input)
        start_time = time.time()
        result = speech_recognizer.recognize_once_async().get()
        end_time = time.time()
        # If something has been recognized by Microsoft
        if result.text:
            sentence = result.text.translate(str.maketrans('', '', string.punctuation)).lower()
            if len(sentence) > 512:
                print("STT string exceeds 512 characters - truncated")
                sentence = sentence[:512]
            if prof_dict:
                t2.join()
                print("T1: T2 has completed the identification")
            now = datetime.now()
            date_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
            with file_lock:
                self.log.write("timestamp:" + date_time_str + "\n")
                self.log.write("chunk_duration:" + str(wav_duration) + "\n")
                self.log.write("chunk_speech_to_text_time:" + str(end_time - start_time) + "\n")
                if prof_dict:
                    self.log.write("chunk_speaker_recognition_time:" +
                                   str(self.speaker_reco_end_time - self.speaker_reco_start_time) + "\n")
            ident_speaker_id = ident_speaker_id[0]
            # Add a turn piece only if the user said something more than the phrase to end the turn
            if sentence:
                turn_piece = TurnPiece(ident_speaker_id, sentence, wav_duration)
                self.dialogue_turn.add_turn_piece(turn_piece)
        else:
            print("T1: Not able to perform speech to text!")
        del speech_recognizer
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
            data = self.stream.read(chunk, exception_on_overflow=False)
            if self.rms(data) >= rms_threshold:
                end = time.time() + split_silence_time
            current = time.time()
            rec.append(data)
            # Limit the audio duration to 1 minute
            if time.time() > timeout:
                break
        end_time = time.time()
        wav_duration = end_time - start_time
        self.prev_input = []
        self.write(b''.join(rec), wav_duration)

    def write(self, recording, wav_duration):
        date_time = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(os.getcwd(), '{}.wav'.format(date_time))
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(self.p.get_sample_size(audio_format))
        wf.setframerate(rate)
        wf.writeframes(recording)
        wf.close()
        print('*** Recording saved. Return to listening ***')
        # print('Written to file: {}'.format(filename))
        if self.mode == "continuous":
            self.t1 = threading.Thread(target=self.speech_and_speaker_recognition, args=(filename, wav_duration,))
            self.t1.start()
        else:
            self.t1 = threading.Thread(target=self.speech_recognition, args=(filename,))
            self.t1.start()

    def listen_continuous(self, server_recorder_socket):
        while True:
            print("*** Waiting for the client to connect ***")
            connection, address = server_recorder_socket.accept()
            print("*** Waiting for client to be ready ***")
            connection.recv(256).decode('utf-8')
            self.stream.start_stream()
            print("*** Listening ***")
            while True:
                self.dialogue_turn = DialogueTurn()
                current = time.time()
                end = time.time() + final_silence_time
                while current <= end:
                    audio_input = self.stream.read(chunk, exception_on_overflow=False)
                    rms_val = self.rms(audio_input)
                    if rms_val > rms_threshold:
                        self.record()
                        end = time.time() + final_silence_time
                    else:
                        self.prev_input.append(audio_input)
                        if len(self.prev_input) > self.max_chunks:
                            self.prev_input = self.prev_input[1:]
                        current = time.time()
                if self.dialogue_turn.get_text() not in ["", " "]:
                    self.stream.stop_stream()
                    time_after_final_silence = time.time()
                    # as soon as the user has finished talking, send an ack to the server
                    connection.send("user finished talking".encode('utf-8'))
                    # To check if client is still connected and has received the message
                    client_msg = connection.recv(256).decode('utf-8')
                    if client_msg == "":
                        print("*** Client disconnected from socket! ***")
                        break
                    print("*** Waiting for last thread to finish transcription ***")
                    self.t1.join()
                    time_after_final_chunk_transcription = time.time()
                    with file_lock:
                        final_delay = time_after_final_chunk_transcription - time_after_final_silence
                        self.log.write("final_delay_time:" + str(final_delay) + "\n")
                        self.log.write("********************\n")
                    print("Recognized string:", self.dialogue_turn.get_text())
                    xml_string = self.dialogue_turn.to_xml_string()
                    print("*** Sending to client:", xml_string)
                    # Useless to surround with a try - except because send does not care
                    connection.send(xml_string.encode('utf-8'))
                    print("*** Waiting for client to be ready ***")
                    client_msg = connection.recv(256).decode('utf-8')
                    if client_msg == "":
                        print("*** Client disconnected from socket! ***")
                        break
                    # Empty the dialogue turn in case in the meanwhile a thread has written something
                    self.dialogue_turn = DialogueTurn()
                    self.stream.start_stream()
                    print("*** Listening ***")

    def listen_wait(self, server_recorder_socket):
        while True:
            print("*** Waiting for the client to connect ***")
            connection, address = server_recorder_socket.accept()
            print("*** Waiting for client to be ready ***")
            connection.recv(256).decode('utf-8')
            self.stream.start_stream()
            print("*** Listening ***")
            sentence_type = ""

            while True:
                self.dialogue_turn = DialogueTurn()
                current = time.time()
                end = time.time() + final_silence_time
                if sentence_type == "w":
                    while True:
                        if any(elem in self.dialogue_turn.get_text() for elem in exit_keywords):
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
                if self.dialogue_turn.get_text() not in ["", " "]:
                    self.stream.stop_stream()
                    print("Recognized string:", self.dialogue_turn.get_text())
                    xml_string = self.dialogue_turn.to_xml_string()
                    print("*** Sending to client:", xml_string)
                    # Useless to surround with a try - except because send does not care
                    connection.send(xml_string.encode('utf-8'))
                    print("*** Waiting for client to be ready ***")
                    sentence_type = connection.recv(256).decode('utf-8')
                    if sentence_type == "":
                        print("*** Client disconnected from socket! ***")
                        break
                    # Empty the dialogue turn in case in the meanwhile a thread has written something
                    self.dialogue_turn = DialogueTurn()
                    self.stream.start_stream()
                    print("*** Listening ***")

    def listen_once(self):
        self.mode = "once"
        print("*** Listening ***")
        self.recognized_text = ""
        self.stream.start_stream()
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
            if self.recognized_text != "":
                self.stream.stop_stream()
                self.recognized_text = self.recognized_text.strip()
                print("Recognized string:", self.recognized_text)
                return self.recognized_text
