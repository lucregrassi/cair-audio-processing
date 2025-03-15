"""
Authors:     Lucrezia Grassi (concept, design and code writing),
             Carmine Tommaso Recchiuto (concept and design),
             Antonio Sgorbissa (concept and design)
Email:       lucrezia.grassi@edu.unige.it
Affiliation: RICE, DIBRIS, University of Genoa, Italy

This script logs data related to the dialogue and vision from the client
"""
import socket
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
log_dialogue_filename = os.path.join(script_dir, "logs", "home_paraplegia", "client_dialogue_log_home_paraplegia_S3.txt")
log_vision_filename = os.path.join(script_dir, "logs", "home_paraplegia", "client_vision_log_home_paraplegia_S3.txt")
print(f"Logging client dialogue to: {log_dialogue_filename}")
print(f"Logging client vision to: {log_vision_filename}")

if __name__ == '__main__':
    # Create the socket - server side: waits for the client to connect
    server_recorder_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_recorder_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_recorder_socket.bind(("0.0.0.0", 9092))
    server_recorder_socket.listen(1)

    while True:
        print("** Waiting for client to connect")
        connection, address = server_recorder_socket.accept()
        print("** Waiting for client to be ready")
        accumulated_data = ""
        messages = []

        while True:
            data_chunk = connection.recv(1024).decode('utf-8')
            print("* Data received *")
            print(data_chunk)
            if not data_chunk:
                print("Client disconnected!")
                break
            accumulated_data += data_chunk
            messages = accumulated_data.split("\n")
            # Process complete messages and update accumulated_data with any remaining partial message
            for i in range(len(messages)-1):
                print(messages[i])
                if messages[i]:
                    if messages[i].split("#")[0] == "d":
                        with open(log_dialogue_filename, 'a+') as dialogue_logfile:
                            dialogue_logfile.write(messages[i].split("#")[1] + "\n")
                    else:
                        with open(log_vision_filename, 'a+') as vision_logfile:
                            vision_logfile.write(messages[i].split("#")[1] + "\n")

            # The last element might be a partial message
            accumulated_data = messages[-1]



