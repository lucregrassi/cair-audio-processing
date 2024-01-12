"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains the methods used to recognize speakers connecting to Microsoft APIs
"""
import time

from dotenv import load_dotenv, find_dotenv
import requests
import pyaudio
import wave
import os

endpoint = "https://cairspeakerrecognition.cognitiveservices.azure.com"
_ = load_dotenv(find_dotenv())
subscription_key = os.getenv("COGNITIVE_SERVICE_KEY")


def from_speech_to_wav(output_filename):
    chunk = 1024
    audio_format = pyaudio.paInt16
    channels = 1
    rate = 44100
    record_seconds = 30
    p = pyaudio.PyAudio()

    stream = p.open(format=audio_format,
                    channels=channels,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk)

    print("** Recording **")

    frames = []

    for i in range(0, int(rate / chunk * record_seconds)):
        data = stream.read(chunk)
        frames.append(data)

    print("** Recording completed **")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(output_filename, 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(p.get_sample_size(audio_format))
    wf.setframerate(rate)
    wf.writeframes(b''.join(frames))
    wf.close()


def get_profiles():
    prof_ids = []
    print("\nRetrieving profiles...")
    url = endpoint + "/speaker/identification/v2.0/text-independent/profiles"
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    response = requests.request("GET", url, headers=headers)
    for profile in response.json()['profiles']:
        profile_id = profile['profileId']
        print(profile_id)
        prof_ids.append(profile_id)
    return prof_ids


def delete_profile(profile_id):
    print("\nDeleting", profile_id)
    url = endpoint + "/speaker/identification/v2.0/text-independent/profiles/" + profile_id
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    requests.request("DELETE", url, headers=headers)


def create_profile():
    print("\nCreating new profile")
    url = endpoint + "/speaker/identification/v2.0/text-independent/profiles"

    raw_data = "{'locale': 'en-us'}"

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=raw_data)
    print(response.text)
    new_profile_id = response.json()['profileId']
    return new_profile_id


def create_enrollment(new_profile_id, filename):
    print("\nCreating enrollment for", new_profile_id)
    url = endpoint + "/speaker/identification/v2.0/text-independent/profiles/" + new_profile_id + "/enrollments"
    data = open(filename, 'rb')

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000'
    }

    response = requests.request("POST", url, headers=headers, data=data)
    print(response.json())


def identify_speaker(prof_ids, filename):
    url = endpoint + "/speaker/identification/v2.0/text-independent/profiles/identifySingleSpeaker?" \
                     "profileIds=" + prof_ids + "&ignoreMinLength=true"

    data = open(filename, 'rb')

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Content-Type': 'audio/wav; codecs=audio/pcm; samplerate=16000'
    }

    response = requests.request("POST", url, headers=headers, data=data)
    # print(response.json())
    try:
        identified_speaker = response.json()['profilesRanking'][0]["profileId"]
        confidence = response.json()["identifiedProfile"]["score"]
    except:
        identified_speaker = "00000000-0000-0000-0000-000000000000"
        confidence = 0
    return identified_speaker, confidence

# Delete all profiles
# profile_ids = get_profiles()
# print(profile_ids)
# for prof_id in profile_ids:
#     delete_profile(prof_id)
# Delete the file
# os.remove("profiles.json")

# Load the content of the file, if exists
# if os.path.isfile("profiles.json"):
#    with open('profiles.json', 'r', encoding='utf-8') as f:
#        profiles_dict = json.load(f)
# else:
#    profiles_dict = {}

# print("Profiles dictionary:", profiles_dict)

# Create profile
# new_id = create_profile()
# name = input("Name: ")
# profiles_dict[new_id] = name
# print("New profile created for", name, "with id", new_id)
# print(profiles_dict)
# with open('profiles.json', 'w', encoding='utf-8') as f:
#    json.dump(profiles_dict, f, ensure_ascii=False, indent=4)

# Enroll new profile
# create_enrollment("60a34301-b201-4dde-80b1-2629e528ccd4", "60a34301-b201-4dde-80b1-2629e528ccd4/20220405-183151.wav")

# from_speech_to_wav("output.wav")

# Delete profiles from dictionary
# if profile_id in profiles_dict.keys():
#     del profiles_dict[profile_id]
# Delete data from file
# if os.path.isfile("profiles.json"):
#     os.remove("profiles.json")

# create_enrollment("5a138df0-34ec-4807-93a5-ffcfa1658b6f", "5a138df0-34ec-4807-93a5-ffcfa1658b6f/20221202-120642.wav")

# delete_profile("f3cb60c4-553a-4c47-9b80-e7276506f0ae")
