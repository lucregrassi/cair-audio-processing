"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains the methods used to register a new user
"""
from speaker_recognition_util import *
from Recorder import Recorder
import azure.cognitiveservices.speech as speechsdk
import socket
import time
import os
import json
import argparse


# This method creates a new profile by calling Microsoft APIs, sends it through the socket to the client and returns
# the corresponding id
def new_profile_creation(socket_connection):
    socket_connection.recv(256).decode('utf-8')
    prof_id = create_profile()
    # Create a new folder in which the wav file for the profile enrollment will be saved
    try:
        os.mkdir(prof_id)
    except OSError:
        print("Creation of the directory %s failed" % prof_id)
    else:
        print("Successfully created the directory %s " % prof_id)
    # Return the new profile id to the client
    socket_connection.send(prof_id.encode('utf-8'))
    return prof_id


# This method acquires the name of the user by getting the transcription of the audio stream using Microsoft APIs and
# sends the name to the client
def acquire_user_name(socket_connection):
    socket_connection.recv(256).decode('utf-8')
    user_name = ""
    print("*** Listening ***")
    while user_name == "":
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language=language)
        result = speech_recognizer.recognize_once_async().get()
        user_name = result.text.strip('.?!')
    print("New user name:", user_name)
    # user_name = input("Confirm name:")
    socket_connection.send(user_name.encode('utf-8'))
    return user_name


# This method acquires the gender of the user by getting the transcription of the audio stream using Microsoft APIs and
# sends the gender to the client
def acquire_user_gender(socket_connection):
    socket_connection.recv(256).decode('utf-8')
    user_gender = ""
    print("*** Listening ***")
    while user_gender == "":
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language=language)
        result = speech_recognizer.recognize_once_async().get()
        user_gender = result.text.strip('.?!').lower()
    print("New user gender:", user_gender)
    female_list = ["female", "femmina", "femminile", "donna", "f", "w"]
    male_list = ["male", "maschio", "maschile", "uomo", "m"]
    if any(word in user_gender for word in female_list):
        user_gender = "f"
    elif any(word in user_gender for word in male_list):
        user_gender = "m"
    else:
        user_gender = "nb"
    # user_gender = input("Confirm gender:")
    socket_connection.send(user_gender.encode('utf-8'))
    return user_gender


# This method acquires the name of the user by getting the transcription of the audio stream using Microsoft APIs and
# sends the name to the client
def acquire_user_age(socket_connection):
    socket_connection.recv(256).decode('utf-8')
    user_age = ""
    # result = r.listen_once()
    # user_name = result.strip('.?!')
    while user_age == "":
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, language=language)
        result = speech_recognizer.recognize_once_async().get()
        user_age = result.text.strip('.?!').lower()
    # print("New user age:", user_name)
    socket_connection.send(user_age.encode('utf-8'))
    return user_age


def perform_enrollment(socket_connection, prof_id):
    socket_connection.recv(256).decode('utf-8')
    date_time = time.strftime("%Y%m%d-%H%M%S")
    filename = os.path.join(os.getcwd() + "/" + prof_id, '{}.wav'.format(date_time))
    # Wait 5 seconds so that the person starts talking
    time.sleep(5)
    from_speech_to_wav(filename)
    # TODO: comment the previous line and uncomment the following line for testing
    # shutil.copyfile("test_registration.wav", filename)
    # ------------------------------------------------
    create_enrollment(prof_id, filename)
    socket_connection.send("enrollment_completed".encode('utf-8'))


if __name__ == '__main__':
    # Define the program description
    text = 'This is the client for CAIR.'
    # Initiate the parser with a description
    parser = argparse.ArgumentParser(description=text)
    # Add long and short argument
    parser.add_argument("--language", "-l", help="set the language of the client to it or en")
    # Read arguments from the command line
    args = parser.parse_args()
    if not args.language:
        print("No language provided. The default English language will be used.")
        language = "en-US"
    else:
        if args.language == "it-IT":
            language = "it-IT"
        else:
            language = "en-US"
        print("The language has been set to", language)

    speech_config = speechsdk.SpeechConfig(subscription=os.environ["AZURE_SPEECH_KEY"], region="westeurope",
                                           speech_recognition_language=language)

    # Create the socket - server side: waits for the client to connect
    server_recorder_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_recorder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_recorder_socket.bind(("0.0.0.0", 9091))
    server_recorder_socket.listen(1)

    if os.path.isfile("profiles.json"):
        with open('profiles.json', 'r', encoding='utf-8') as f:
            profiles_dict = json.load(f)
    else:
        profiles_dict = {}

    while True:
        print("*** Waiting for client to connect ***")
        connection, address = server_recorder_socket.accept()
        # ** STEP 1 ** Create a new profile on the speaker recognition Microsoft API
        profile_id = new_profile_creation(connection)

        r = Recorder(language)
        # ** STEP 2 ** Wait for the client to ask for the transcription of the name of the new profile
        profile_name = acquire_user_name(connection)

        # ** STEP 4 ** Wait for the client to ask for the transcription of the gender of the new profile
        profile_gender = acquire_user_gender(connection)

        # ** STEP 5 ** Wait for the client to ask for the transcription of the gender of the new profile
        profile_age = acquire_user_age(connection)

        # ** STEP 6 ** Listen to the audio input for 30 seconds, save it in a wav file inside the folder created above
        # and send it to Microsoft Speaker Recognition APIs for the enrollment of the new profile.
        print("Starting enrollment procedure")
        perform_enrollment(connection, profile_id)
        print(profile_name + "'s enrollment completed!")
        # Write the information about the new user in the profiles.json file
        profiles_dict[profile_id] = profile_name
        with open('profiles.json', 'w', encoding='utf-8') as f:
            json.dump(profiles_dict, f, ensure_ascii=False, indent=4)
