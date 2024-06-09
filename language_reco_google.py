import speech_recognition as sr
from googletrans import Translator

import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "cairclient-b143a5b4ff58.json"


def recognize_language(text):
    translator = Translator()
    detected = translator.detect(text)
    return detected.lang, detected.confidence


def transcribe_audio():
    # Initialize recognizer
    recognizer = sr.Recognizer()

    # List available microphones to ensure the correct one is selected
    mic_list = sr.Microphone.list_microphone_names()
    print("Available microphones:")
    for index, name in enumerate(mic_list):
        print(f"{index}: {name}")

    # Using the default microphone
    with sr.Microphone() as source:
        print("Please speak something...")

        # Adjust for ambient noise
        print("Calibrating for ambient noise, please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=5)  # Increase duration if necessary
        print("Calibration complete. Start speaking.")

        # Listen for the first phrase and extract it into audio data
        audio = recognizer.listen(source, timeout=10,
                                  phrase_time_limit=10)  # Increase timeout and phrase_time_limit if necessary

        try:
            print("Transcribing audio...")
            # Transcribe audio using Google Web Speech API
            text = recognizer.recognize_google_cloud(audio)
            print(f"Transcription: {text}")

            # Detect language
            lang, confidence = recognize_language(text)
            print(f"Detected language: {lang} with confidence: {confidence}")

        except sr.UnknownValueError:
            print("Google Web Speech could not understand the audio.")
        except sr.RequestError as e:
            print(f"Could not request results from Google Web Speech service; {e}")


if __name__ == "__main__":
    transcribe_audio()
