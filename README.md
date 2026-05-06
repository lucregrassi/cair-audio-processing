# CAIR Audio Processing
Audio recording and speaker recognition service for CAIR-based applications.
The repository provides a Python service that records audio from a microphone, detects speech activity, transcribes speech with Microsoft Azure Speech Services, and identifies registered speakers through Azure Speaker Recognition.

## Features
- Microphone audio recording
- Voice Activity Detection with WebRTC VAD
- Speech-to-text with Azure Speech Services
- Speaker identification with Azure Speaker Recognition
- Speaker profile registration
- Profile deletion utility
- TCP socket interface for external clients
- Raspberry Pi/Linux startup script

## Requirements

* Python 3.9+
* Microphone supported by PyAudio
* Microsoft Azure Speech resource
* Azure Speech API key

## Installation

Follow the steps detailed in the [Developer Guide](Raspberry_developer_guide_it.pdf)
