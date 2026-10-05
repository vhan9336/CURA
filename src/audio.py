# audio.py
import numpy as np
import sounddevice as sd
import flet as ft
from datetime import datetime
THRESHOLD = 0.1
DURATION = 0.1
SAMPLE_RATE = 44100


def start_listening(page: ft.Page):
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)

        volume_norm = np.linalg.norm(indata) / np.sqrt(len(indata))

        # Optional: uncomment if you want to see every volume check
        # print(f"Audio logged; Volume Level: {volume_norm:.2f}")

        if volume_norm > THRESHOLD:
            print(f"\033[31mAudio system triggered! Volume level: {volume_norm:.2f}\033[0m")
            if hasattr(page, "go_to_confirm"):
                page.go_to_confirm()

    with sd.InputStream(
            callback=audio_callback, channels=1, samplerate=SAMPLE_RATE
    ):
        print("Listening for loud noises...")
        while True:
            now = datetime.now()
            sd.sleep(int(DURATION * 1000))
            print(f"Audio frame logged; {now}")