"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains the Recorder class that acquires data from the microphone every time the noise exceeds an RMS threshold.
The audio is split each t seconds and transcribed using Microsoft APIs.
Once a T second silence has elapsed or a passphrase is recognized, first the client is informed that the user has finished
speaking, then the result of the whole transcription is returned. If nobody talks for more than n seconds, the Recorder
sends a message to the client so that it can decide whether to do something or to return to listening.
The class also gives the possibility of performing just a single recognition and returns the result.
"""

from cair_libraries.dialogue_turn import DialogueTurn, TurnPiece
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

rms_threshold = 60
short_normalize = (1.0 / 32768.0)

# rate for PC and Raspberry Pi
rate = 44100
# Rate for AlterEgo
# rate = 192000
chunk = 4096
frames_per_buffer = 8192
audio_format = pyaudio.paInt16
channels = 1

s_width = 2
split_silence_time = 0.5
final_silence_time = 2
exit_keywords = ["passo e chiudo", "cosa ne pensi"]

# Seconds of silence after which the audio recorder writes "timeout" on the socket
TIMEOUT = 30


def print_colored(message, color):
    """Prints an error message in red."""
    if color == "red":
        print(f"\033[91m{message}\033[0m")
    elif color == "blue":
        print(f"\033[94m{message}\033[0m")
    elif color == "green":
        print(f"\033[92m{message}\033[0m")


class Recorder:
    def __init__(self, lang, auto_detect_language=True):
        self.auto_detect_language = auto_detect_language
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=audio_format, channels=channels, rate=rate, input=True, output=False,
                                  frames_per_buffer=frames_per_buffer, start=False)
        self.prev_input = []
        self.max_chunks = 20
        # Initialize object that will contain the data related to the dialogue turn
        self.dialogue_turn = DialogueTurn()
        self.recognized_text = ""
        self.mode = "continuous"
        self.root = ET.Element("response")
        self.speech_config = speechsdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"],
                                                    region="westeurope", speech_recognition_language=lang)
        self.t1 = threading.Thread(target=self.speech_and_speaker_recognition, args=("", 0,))

        self.speaker_reco_start_time = 0
        self.speaker_reco_end_time = 0
        self.log_buffer = {}
        self.chunk_counter = 0

    def accumulate_log(self, key, value):
        self.log_buffer[key] = value

    def clear_log(self):
        self.log_buffer.clear()

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
            self.accumulate_log("speech_to_text_time", end_time - start_time)
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

        # Delete the original wav file without final silence
        if os.path.exists(wav_filename):
            os.remove(wav_filename)

    def speech_and_speaker_recognition(self, wav_filename, wav_duration):
        if os.path.isfile("profiles.json"):
            with open('profiles.json', 'r', encoding='utf-8') as f:
                prof_dict = json.load(f)
        else:
            prof_dict = {}
        # Specify where the audio should be taken
        audio_config = speechsdk.AudioConfig(filename=wav_filename)

        ident_speaker_id = ["00000000-0000-0000-0000-000000000000"]
        t2 = threading.Thread(target=self.speaker_recognition, args=(format(wav_filename), prof_dict, ident_speaker_id))
        if prof_dict:
            t2.start()

        # Configure the speech_recognizer based on the auto_detect_language parameter
        if self.auto_detect_language:
            # If there are no speaker registered and no one has talked, auto-detect the language to add tag to xml
            if self.dialogue_turn.is_empty():
                print("Performing speech to text with auto-detection of language...")
                auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
                    languages=["en-US", "it-IT"]
                )
                speech_recognizer = speechsdk.SpeechRecognizer(
                    speech_config=self.speech_config,
                    audio_config=audio_config,
                    auto_detect_source_language_config=auto_detect_source_language_config
                )
            else:
                speech_recognizer = speechsdk.SpeechRecognizer(
                    speech_config=self.speech_config,
                    audio_config=audio_config
                )
        else:
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
        start_time = time.time()
        # Attendi il risultato del riconoscimento vocale
        result = speech_recognizer.recognize_once()
        end_time = time.time()
        # Se qualcosa è stato riconosciuto
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            if self.auto_detect_language:
                if self.dialogue_turn.is_empty():
                    # Extract the recognized language and redefine the speech config object for future recognitions.
                    language = result.properties[
                        speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult]
                    self.speech_config = speechsdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"],
                                                                region="westeurope",
                                                                speech_recognition_language=language)
                else:
                    language = ""
            else:
                language = self.speech_config.speech_recognition_language
            sentence = result.text.translate(str.maketrans('', '', string.punctuation)).lower()
            if len(sentence) > 512:
                print("STT string exceeds 512 characters - truncated")
                sentence = sentence[:512]
            if prof_dict:
                t2.join()
                print("T1: T2 has completed the identification")
            now = datetime.now()
            self.chunk_counter += 1
            self.accumulate_log("timestamp", now.strftime("%Y-%m-%d %H:%M:%S"))
            self.accumulate_log(f"chunk_{self.chunk_counter}_duration", wav_duration)
            self.accumulate_log(f"chunk_{self.chunk_counter}_speech_to_text_time", end_time - start_time)
            if prof_dict:
                self.accumulate_log(f"chunk_{self.chunk_counter}_speaker_recognition_time",
                                    self.speaker_reco_end_time - self.speaker_reco_start_time)
            ident_speaker_id = ident_speaker_id[0]
            # Add a turn piece only if the user said something more than the phrase to end the turn
            if sentence:
                turn_piece = TurnPiece(ident_speaker_id, sentence, language, wav_duration)
                self.dialogue_turn.add_turn_piece(turn_piece)
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("T1: No speech recognized.")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print(f"T1: Recognition canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"T1: Error details: {cancellation_details.error_details}")
        del speech_recognizer

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
        print_colored("Noise detected: start recording", "blue")
        rec = []
        if self.prev_input:
            for c in self.prev_input:
                rec.append(c)

        start_time = time.time()
        current = time.time()
        end = time.time() + split_silence_time
        timeout = time.time() + 30
        while current <= end:
            # read_available = self.stream.get_read_available()
            # print(f"stream data available: {read_available}")
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
        print_colored("Recording saved. Return to listening", "green")
        if self.mode == "continuous":
            self.t1 = threading.Thread(target=self.speech_and_speaker_recognition, args=(filename, wav_duration,))
            self.t1.start()
        else:
            self.t1 = threading.Thread(target=self.speech_recognition, args=(filename,))
            self.t1.start()

    def listen_continuous(self, microphone_socket):
        while True:
            print_colored("Waiting for the client to connect", "blue")
            connection, address = microphone_socket.accept()
            print_colored("Waiting for client to be ready", "blue")
            connection.recv(256).decode('utf-8')
            self.stream.start_stream()
            # Initialize start time for timeout
            timeout_start_time = time.time()
            print_colored("Listening", "green")
            while True:
                self.dialogue_turn = DialogueTurn()
                # Update times for final silence
                current = time.time()
                end = time.time() + final_silence_time
                timeout = False
                while current <= end:
                    # read_available = self.stream.get_read_available()
                    # print(f"stream data available: {read_available}")
                    audio_input = self.stream.read(chunk, exception_on_overflow=False)
                    rms_val = self.rms(audio_input)
                    if rms_val > rms_threshold:
                        self.record()
                        print("Reset end time and start of silence")
                        end = time.time() + final_silence_time
                        timeout_start_time = time.time()
                    else:
                        timeout_end_time = time.time()
                        if timeout_end_time - timeout_start_time > TIMEOUT:
                            timeout = True
                            print_colored("SILENCE TIMEOUT", "red")
                            connection.send("timeout".encode('utf-8'))
                            self.chunk_counter = 0
                            break
                        self.prev_input.append(audio_input)
                        if len(self.prev_input) > self.max_chunks:
                            self.prev_input = self.prev_input[1:]
                        current = time.time()

                if self.dialogue_turn.get_text() not in ["", ""] or timeout:
                    print("Something recognized or timeout")
                    self.stream.stop_stream()
                    if not timeout:
                        time_after_final_silence = time.time()
                        # as soon as the user has finished talking, send an ack to the server
                        connection.send("user finished talking".encode('utf-8'))
                        # To check if a client is still connected and has received the message
                        client_msg = connection.recv(256).decode('utf-8')
                        if client_msg == "":
                            print("Client disconnected from socket!")
                            break
                        print("Waiting for last thread to finish transcription")
                        self.t1.join()
                        time_after_final_chunk_transcription = time.time()

                        final_delay = time_after_final_chunk_transcription - time_after_final_silence
                        self.accumulate_log("final_delay_time", final_delay)
                        final_payload = {
                            "transcription": self.dialogue_turn.to_xml_string(),
                            "logs": self.log_buffer
                        }
                        print("Recognized string:", self.dialogue_turn.get_text())
                        print("Sending to client:", final_payload)
                        # Useless to surround with a try - except because send does not care
                        connection.sendall(json.dumps(final_payload).encode('utf-8'))
                        self.clear_log()
                        self.chunk_counter = 0
                    print_colored("Waiting for client to be ready", "blue")
                    client_msg = connection.recv(256).decode('utf-8')
                    if client_msg == "":
                        print_colored("Client disconnected from socket!", "red")
                        break
                    # Empty the dialogue turn in case in the meanwhile a thread has written something
                    self.dialogue_turn = DialogueTurn()
                    self.stream.start_stream()
                    # Reset timeout start time
                    timeout_start_time = time.time()
                    print_colored("Listening", "green")

    def listen_wait(self, server_recorder_socket):
        while True:
            print_colored("Waiting for the client to connect", "blue")
            connection, address = server_recorder_socket.accept()
            print_colored("Waiting for client to be ready", "blue")
            connection.recv(256).decode('utf-8')
            self.stream.start_stream()
            print_colored("Listening", "green")
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
                    print("Sending to client:", xml_string)
                    # Useless to surround with a try - except because send does not care
                    connection.send(xml_string.encode('utf-8'))
                    self.clear_log()
                    self.chunk_counter = 0
                    print_colored("Waiting for client to be ready", "blue")
                    sentence_type = connection.recv(256).decode('utf-8')
                    if sentence_type == "":
                        print_colored("Client disconnected from socket!", "red")
                        break
                    # Empty the dialogue turn in case in the meanwhile a thread has written something
                    self.dialogue_turn = DialogueTurn()
                    self.stream.start_stream()
                    print_colored("Listening", "green")

    def listen_once(self):
        self.mode = "once"
        print_colored("Listening", "green")
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
