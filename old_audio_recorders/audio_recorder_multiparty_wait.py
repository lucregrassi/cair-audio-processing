"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This file contains a script that acquires data from the microphone everytime the noise exceeds a rms threshold.
The audio is split each t seconds, and it is transcribed using microsoft APIs.
Once a passphrase is recognized the whole text is transcribed, tagged and sent to the client.
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
    a.listen_wait(server_recorder_socket)
