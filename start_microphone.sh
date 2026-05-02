#!/bin/bash
export PATH=/usr/bin:/bin:/usr/local/bin
export XDG_RUNTIME_DIR=/run/user/$(id -u)

sleep 10
cd /home/rice/cair-audio-processing

exec /home/rice/cair-audio-processing/venv/bin/python /home/rice/cair-audio-processing/audio_recorder.py