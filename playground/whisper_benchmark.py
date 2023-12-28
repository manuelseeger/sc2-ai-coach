import whisper
import torch
import datetime
import pyaudio
import wave

pyaudio = pyaudio.PyAudio()
import speech_recognition as sr

from io import BytesIO


def playback(audio):
    # open stream based on the wave object which has been input.
    stream = pyaudio.open(
        format=pyaudio.get_format_from_width(audio.getsampwidth()),
        channels=audio.getnchannels(),
        rate=audio.getframerate(),
        output=True,
    )

    # read data (based on the chunk size)
    data = audio.readframes(1024)

    # play stream (looping from beginning of file to the end)
    while data:
        # writing to the stream is what *actually* plays the sound.
        stream.write(data)
        data = audio.readframes(1024)

    # cleanup stuff.
    audio.close()
    stream.close()
    # pyaudio.terminate()


"""
if torch.cuda.is_available():
    device = torch.device("cuda:0")
    print("GPU")
    print(torch.cuda.current_device())
    print(torch.cuda.device(0))
    print(torch.cuda.get_device_name(0))
else:
    device = torch.device("cpu")
    print("CPU")

t0 = datetime.datetime.now()
print(f"Load Model at  {t0}")
model = whisper.load_model("base.en").to(device)
t1 = datetime.datetime.now()
print(f"Loading took {t1-t0}")
print(f"started at {t1}")

# do the transcription
output = model.transcribe("obs/harstem samples/harstem sample 02.ogg")

# show time elapsed after transcription is complete.
t2 = datetime.datetime.now()
print(f"ended at {t2}")
print(f"time elapsed: {t2 - t1}")

print(output["text"])
"""

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

        # prompt = self.transcribe(audio)

        playback(wf)
