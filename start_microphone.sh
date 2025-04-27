#!/bin/bash
export PATH=/usr/bin:/bin:/user/local/bin
export XDG_RUNTIME_DIR=/run/user/$(id -u)
sleep 10
cd /home/rice/cair-audio-processing
source /home/rice/cair-audio-processing/venv/bin/activate
python3 /home/rice/cair-audio-processing/audio_recorder.py > /home/rice/audio_recorder_log.txt 2>&1 &