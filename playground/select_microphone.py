import wave
from io import BytesIO

import pyaudio
import speech_recognition as sr

pyaudio = pyaudio.PyAudio()


def playback(audio):
    stream = pyaudio.open(
        format=pyaudio.get_format_from_width(audio.getsampwidth()),
        channels=audio.getnchannels(),
        rate=audio.getframerate(),
        output=True,
    )

    data = audio.readframes(1024)

    while data:
        stream.write(data)
        data = audio.readframes(1024)

    audio.close()
    stream.close()


print("Available audio input devices:")
input_devices = []
for i in range(pyaudio.get_device_count()):
    dev = pyaudio.get_device_info_by_index(i)
    if dev.get("maxInputChannels"):
        input_devices.append(i)
        print(i, dev.get("name"))

microphone_index = int(input("Select microphone: "))

microphone = sr.Microphone(device_index=microphone_index)
recognizer = sr.Recognizer()

# minimum audio energy to consider for recording
recognizer.energy_threshold = 400
recognizer.dynamic_energy_threshold = True
recognizer.dynamic_energy_adjustment_damping = 0.15
recognizer.dynamic_energy_ratio = 1.5
# seconds of non-speaking audio before a phrase is considered complete
recognizer.pause_threshold = 0.5
# seconds after an internal operation (e.g., an API request) starts before it times out, or ``None`` for no timeout
recognizer.operation_timeout = None

# minimum seconds of speaking audio before we consider the speaking audio a phrase - values below this are ignored (for filtering out clicks and pops)
recognizer.phrase_threshold = 0.3
# seconds of non-speaking audio to keep on both sides of the recording
recognizer.non_speaking_duration = 0.2


while True:
    with microphone as source:
        print(">>>")
        audio = recognizer.listen(source)
        print("Got voice input")

        wfile = BytesIO(audio.get_wav_data())

        wf = wave.open(wfile, "rb")

        playback(wf)
