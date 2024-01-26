import thesis_csv
import os.path
from datetime import datetime

microphone_log_filename = "microphone_log_controlled_neutral_tone.txt"
microphone_csv_output_filename = microphone_log_filename.split('.')[0] + ".csv"
client_dialogue_log_filename = "client_dialogue_log_controlled_neutral_tone.txt"
client_dialogue_csv_output_filename = client_dialogue_log_filename.split('.')[0] + ".csv"
client_vision_log_filename = "client_vision_log_controlled_neutral_tone.txt"
client_vision_csv_output_filename = client_vision_log_filename.split('.')[0] + ".csv"


# Load data from log file and transform it into a csv where each line corresponds to a turn
def from_log_to_csv(log_filename, csv_headers):
    current_data = {}
    data_list = []
    with open(log_filename, 'r') as file:
        lines = file.readlines()

    # Iterate through log file lines
    for line in lines:
        print(line)
        # Ignore delimitation lines and every time there is one, add the dictionary to the list
        if line.strip() == '********************' or log_filename == microphone_log_filename and "timestamp" in line:
            if current_data:
                for value in csv_headers:
                    if value not in current_data.keys():
                        current_data[value] = ""
                data_list.append(current_data)
                current_data = {}
                if "timestamp" in line:
                    # Split the line by key and value
                    key, value = line.strip().split(':', 1)
                    current_data[key] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
                continue

        # Split the line by key and value
        key, value = line.strip().split(':', 1)

        # Format timestamp column
        if key == 'timestamp':
            current_data[key] = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        elif "_time" in key or "_bytes" in key:
            current_data[key] = value
        else:
            current_data[key] = value.lower()

    # Crea il file CSV
    with open("csv/" + log_filename.split('.')[0] + ".csv", 'w', newline='') as csv_file:
        csv_writer = thesis_csv.DictWriter(csv_file, fieldnames=csv_headers)
        # write the headers in the csv
        csv_writer.writeheader()
        # write data in the csv
        csv_writer.writerows(data_list)


choice = input("Choose log file to process: \n1) Microphone\n2) Client dialogue \n3) Client vision\n")
if choice == '1':
    if os.path.isfile(microphone_log_filename):
        csv_microphone_headers = ['timestamp', 'chunk_duration', 'chunk_speech_to_text_time', 'chunk_speaker_recognition_time',
                                  'final_delay_time']
        from_log_to_csv(microphone_log_filename, csv_microphone_headers)
elif choice == '2':
    if os.path.isfile(client_dialogue_log_filename):
        csv_client_dialogue_headers = ['timestamp', 'ack_sentence_speaking_time', 'first_request_response_time',
                                       'second_request_response_time', 'first_sentence_speaking_time',
                                       'second_sentence_speaking_time']
        from_log_to_csv(client_dialogue_log_filename, csv_client_dialogue_headers)
else:
    if os.path.isfile(client_vision_log_filename):
        csv_client_vision_headers = ['timestamp', 'image_capture_time', 'compressed_image_size_bytes',
                                     'densecap_request_response_time']
        from_log_to_csv(client_vision_log_filename, csv_client_vision_headers)
