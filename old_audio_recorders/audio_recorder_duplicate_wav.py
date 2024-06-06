from Microphone.speaker_reco_util import *
import threading
import pyaudio
import math
import struct
import wave
import time
import os
import json
import azure.cognitiveservices.speech as speechsdk
from pydub import AudioSegment

rms_threshold = 30
SHORT_NORMALIZE = (1.0/32768.0)
chunk = 1024
FORMAT = pyaudio.paInt16
channels = 1
RATE = 16000
swidth = 2
split_silence_time = 1
final_silence_time = 3

f_name_directory = os.getcwd()
speech_config = speechsdk.SpeechConfig(subscription="8f95505a0a7f49edaa75edcf6440dcbf", region="westeurope")


class Recorder:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=FORMAT,
                                  channels=channels,
                                  rate=RATE,
                                  input=True,
                                  output=True,
                                  frames_per_buffer=chunk)
        self.prev_input = []
        self.max_chunks = 20
        self.string_to_send = ""

    def microsoft_sender(self, wav_filename):
        if os.path.isfile("../Microphone/profiles.json"):
            with open('../Microphone/profiles.json', 'r', encoding='utf-8') as f:
                prof_dict = json.load(f)
        else:
            prof_dict = {}
        # print("Profiles dictionary:", prof_dict)
        # print("Sending to microsoft:", wav)
        audio_input = speechsdk.AudioConfig(filename=wav_filename)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
        result = speech_recognizer.recognize_once_async().get()
        print(result.text)
        if result.text and prof_dict:
            # if the audio is less than 4 seconds, add silence at the end
            with wave.open(wav_filename) as mywav:
                duration_seconds = mywav.getnframes() / mywav.getframerate()
            extended_wav_filename = wav_filename[:-4] + "d.wav"
            while duration_seconds < 4.0:
                if os.path.exists(extended_wav_filename):
                    sound1 = AudioSegment.from_file(extended_wav_filename, format="wav")
                else:
                    sound1 = AudioSegment.from_file(wav_filename, format="wav")
                sound2 = AudioSegment.from_file(wav_filename, format="wav")
                extended_wav = sound1 + sound2
                extended_wav.export(extended_wav_filename, format="wav")
                with wave.open(extended_wav_filename) as mywav:
                    duration_seconds = mywav.getnframes() / mywav.getframerate()
                    print("Extended WAV duration:", duration_seconds)

            prof_ids = ','.join(prof_dict.keys())

            if os.path.exists(extended_wav_filename):
                start = time.time()
                ident_speaker_id, confidence = identify_speaker(prof_ids, extended_wav_filename)
                end = time.time()
            else:
                start = time.time()
                ident_speaker_id, confidence = identify_speaker(prof_ids, extended_wav_filename)
                end = time.time()
            print("Request time:", end-start)

            if not ident_speaker_id:
                speaker_name = "Unknown"
                print("Not able to recognize speaker")
            else:
                speaker_name = prof_dict[ident_speaker_id]
                print("Identified speaker:", speaker_name)
                print("Confidence:", confidence)
            self.string_to_send = self.string_to_send + " " + speaker_name + ":" + result.text
            # If it has been created, delete the extended file with final silence
            # if os.path.exists(extended_wav_filename):
            #    os.remove(extended_wav_filename)
        else:
            print("Not able to perform speech to text")
        # Delete the original wav file without final silence
        # os.remove(wav_filename)

    @staticmethod
    def rms(frame):
        count = len(frame) / swidth
        frmt = "%dh" % count
        shorts = struct.unpack(frmt, frame)

        sum_squares = 0.0
        for sample in shorts:
            n = sample * SHORT_NORMALIZE
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

        while current <= end:
            data = self.stream.read(chunk)
            if self.rms(data) >= rms_threshold:
                end = time.time() + split_silence_time
            current = time.time()
            rec.append(data)

        self.prev_input = []
        self.write(b''.join(rec))

    def write(self, recording):
        date_time = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(f_name_directory, '{}.wav'.format(date_time))
        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(recording)
        wf.close()
        print('Written to file: {}'.format(filename))
        with wave.open(filename) as mywav:
            duration_seconds = mywav.getnframes() / mywav.getframerate()
            print("Duration WAV:", duration_seconds)
        t1 = threading.Thread(target=self.microsoft_sender, args=(format(filename),))
        t1.start()
        print('*** Recording saved. Return to listening ***')

    def listen(self):
        print('*** Start Listening ***')
        while True:
            current = time.time()
            end = time.time() + final_silence_time
            while current <= end:
                audio_input = self.stream.read(chunk)
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
                print("String to send to the Hub:", self.string_to_send)
                self.string_to_send = ""


a = Recorder()
a.listen()
