#!/bin/bash
export PATH=/usr/bin:/bin:/user/local/bin
export XDG_RUNTIME_DIR=/run/user/$(id -u)
sleep 10
cd /home/pi/cair-audio-processing
source /home/pi/cair-audio-processing/venv/bin/activate
python3 /home/pi/cair-audio-processing/audio_recorder.py > /home/pi/audio_recorder_log.txt 2>&1 &