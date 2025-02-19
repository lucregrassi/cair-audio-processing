#!/bin/bash
export PATH=/usr/bin:/bin:/user/local/bin
export XDG_RUNTIME_DIR=/run/user/$(id -u)
sleep 30
cd /home/rice/microphone_services
source /home/rice/microphone_services/venv/bin/activate
python3 /home/rice/microphone_services/audio_recorder.py > /home/rice/recorder_out.txt 2>&1 &
python3 /home/rice/microphone_services/acquire_client_log.py > /home/rice/log_out.txt 2>&1 &
