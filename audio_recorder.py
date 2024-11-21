"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains a script that acquires data from the microphone every time the noise exceeds an RMS threshold.
The audio is split each t seconds, and it is transcribed using Microsoft APIs.
After s seconds of silence, the whole sentence is transcribed, tagged, and sent to the client.
"""

from Recorder import Recorder
import argparse
import socket

if __name__ == '__main__':
    global language
    # Define the program description
    text = 'This is the service for detecting noise and start recording.'
    # Initiate the parser with a description
    parser = argparse.ArgumentParser(description=text)
    # Add long and short arguments
    parser.add_argument("--language", "-l", help="Set the language of the audio recorder to en or it")
    parser.add_argument("--auto_detect", "-ad", help="Enable auto-detection of language", action='store_true')

    # Read arguments from the command line
    args = parser.parse_args()
    if not args.language:
        print("No language provided. The default Italian language will be used.")
        language = "it-IT"
    else:
        if args.language == "it":
            language = "it-IT"
        elif args.language == "cn":
            language = "zh-CN"
        else:
            language = "en-GB"
        print("The language of the audio recorder has been set to", language)

    # Set the auto_detect_language variable based on the command-line argument
    auto_detect_language = args.auto_detect
    if auto_detect_language:
        print("Language auto-detection is enabled.")
    else:
        print("Language auto-detection is disabled.")

    # Create the socket - server side: waits for the client to connect
    server_recorder_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_recorder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_recorder_socket.bind(("0.0.0.0", 9090))
    server_recorder_socket.listen(1)

    # Create an instance of the Recorder class with the auto_detect_language parameter
    a = Recorder(language, auto_detect_language)
    a.listen_continuous(server_recorder_socket)
