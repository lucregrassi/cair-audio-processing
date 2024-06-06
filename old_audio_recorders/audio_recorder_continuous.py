import threading

import azure.cognitiveservices.speech as speechsdk
import socket
import time
import json
import pyaudio
import wave

# Socket to which the client should connect
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("130.251.13.147", 9090))
server_socket.listen(1)
print("Waiting for client to connect...")
connection, address = server_socket.accept()


class SpeechRecognition:
    def __init__(self):
        self.listening = False
        self.silence_time = -1
        # This variable is used to store the recognized sentence
        self.recognized_sentence = ""
        self.filename = "output.wav"

    def thread_record(self):
        chunk = 1024
        stream_format = pyaudio.paInt16
        channels = 1
        rate = 44100
        record_seconds = 5

        p = pyaudio.PyAudio()

        stream = p.open(format=stream_format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
        print("* recording")
        frames = []

        for i in range(0, int(rate/chunk * record_seconds)):
            data = stream.read(chunk)
            frames.append(data)

        print("* done recording")

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(stream_format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))
        wf.close()

    def on_recognized(self, evt):
        print("**on recognized:", self.listening)
        # Update sentence only when something has been recognized and when the system should be listening (not when the
        # robot is talking, otherwise it transcribes its own speech)
        if evt.result.text != "" and self.listening:
            # Make the thread start the recording
            self.recognized_sentence = self.recognized_sentence + " " + evt.result.text
            print(self.recognized_sentence.strip())
            self.silence_time = 0

    def from_mic(self):
        speech_config = speechsdk.SpeechConfig(subscription="8f95505a0a7f49edaa75edcf6440dcbf", region="westeurope")
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

        speech_recognizer.session_started.connect(lambda evt: print('*** SESSION STARTED ***'))
        # speech_recognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
        speech_recognizer.recognized.connect(self.on_recognized)

        speech_recognizer.session_stopped.connect(lambda evt: print('*** SESSION STOPPED ***'))
        # speech_recognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))

        print("Waiting for client to be ready...")
        client_msg = connection.recv(256).decode('utf-8')
        print("Client message:", client_msg)
        if client_msg == "":
            print("Client disconnected from socket.")
            exit(0)
        data = json.loads(client_msg)
        reply = data["reply"]
        sentence_type = data["sentence_type"]

        # Start listening
        speech_recognizer.start_continuous_recognition_async()
        self.listening = True
        recording_thread = threading.Thread(target=self.thread_record)
        recording_thread.start()
        for thread in threading.enumerate():
            print(thread.name)

        while True:
            print("Reply:", reply)
            print("Sentence type:", sentence_type)
            # Wait so that it does not recognize what he said before
            time.sleep(2)
            print("*** TALK NOW! ***")
            self.listening = True
            self.recognized_sentence = ""
            self.silence_time = -1
            if sentence_type != 'q':
                while self.silence_time < 6:
                    time.sleep(0.5)
                    if self.silence_time != -1:
                        self.silence_time = self.silence_time + 1
            else:
                while self.recognized_sentence == "":
                    time.sleep(0.5)

            self.listening = False
            self.recognized_sentence = self.recognized_sentence.strip()
            print("SENDING:", self.recognized_sentence)
            connection.send(self.recognized_sentence.encode('utf-8'))

            # Wait for the client to be ready to receive data from the user:
            print("*** WAIT FOR THE CLIENT TO BE READY ***")
            client_msg = connection.recv(256).decode('utf-8')
            if client_msg == "":
                print("*** CLIENT DISCONNECTED FROM SOCKET - STOPPING RECOGNITION... ***")
                speech_recognizer.stop_continuous_recognition_async()
                break
            data = json.loads(client_msg)
            reply = data["reply"]
            sentence_type = data["sentence_type"]


speech_reco = SpeechRecognition()
speech_reco.from_mic()

