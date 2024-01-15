import socket

log_dialogue_filename = "logs/client_dialogue_log.txt"
log_vision_filename = "logs/client_vision_log.txt"

dialogue_logfile = open(log_dialogue_filename, 'a+')
vision_logfile = open(log_vision_filename, 'a+')

if __name__ == '__main__':
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
            print("Data received")
            if not data_chunk:
                print("Client disconnected!")
                break

            accumulated_data += data_chunk
            messages = accumulated_data.split("\n")
            # Process complete messages and update accumulated_data with any remaining partial message
            for i in range(len(messages)-1):
                if messages[i]:
                    if messages[i].split("#")[0] == "d":
                        dialogue_logfile.write(messages[i].split("#")[1] + "\n")
                    else:
                        vision_logfile.write(messages[i].split("#")[1] + "\n")

            # The last element might be a partial message
            accumulated_data = messages[-1]



