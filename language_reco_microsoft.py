import azure.cognitiveservices.speech as speechsdk

import os


def transcribe_and_detect_language(subscription_key, region):
    # Configura il servizio di riconoscimento vocale di Azure
    speech_config = speechsdk.SpeechConfig(subscription=subscription_key, region=region)
    # Aggiungi le lingue che desideri supportare
    auto_detect_source_language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-US", "it-IT", "fr-FR", "es-ES"])

    # Usa il microfono come sorgente audio
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config, auto_detect_source_language_config=auto_detect_source_language_config)

    # TODO: capire differenza con async
    print("Listening...")
    result = speech_recognizer.recognize_once()

    # Controlla il risultato
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        detected_language = result.properties[speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult]
        print(f"Transcription: {result.text}")
        print(f"Detected language: {detected_language}")
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No voice recognized.")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Transcription cancelled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error: {cancellation_details.error_details}")


if __name__ == "__main__":
    subscription_key = os.environ["COGNITIVE_SERVICE_KEY"]
    region = "westeurope"
    transcribe_and_detect_language(subscription_key, region)
