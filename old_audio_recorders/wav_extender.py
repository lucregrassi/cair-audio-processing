import wave
from pydub import AudioSegment


# if the audio is less than 4 seconds, add silence at the end
def extend_wav(wav_filename):
    with wave.open(wav_filename) as mywav:
        duration_seconds = mywav.getnframes() / mywav.getframerate()
        if duration_seconds < 4.0:
            fill_audio_time_ms = (4.0 - duration_seconds)*1000
            silence = AudioSegment.silent(duration=fill_audio_time_ms)  # 1 second
            wav_file = AudioSegment.from_file(wav_filename)
            extended_wav = wav_file + silence
            extended_wav_filename = wav_filename[:-4] + "e.wav"
            extended_wav.export(extended_wav_filename, format='wav')
        else:
            extended_wav_filename = wav_filename