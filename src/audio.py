# audio.py
import numpy as np
import sounddevice as sd
import flet as ft

THRESHOLD = 0.5
DURATION = 0.1
SAMPLE_RATE = 44100


def start_listening(page: ft.Page):
    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)

        volume_norm = np.linalg.norm(indata) / np.sqrt(len(indata))

        if volume_norm > THRESHOLD:
            print(f"⚠️ Loud noise detected! Volume level: {volume_norm:.2f}")
            if hasattr(page, "go_to_confirm"):
                page.go_to_confirm()

    with sd.InputStream(
            callback=audio_callback, channels=1, samplerate=SAMPLE_RATE
    ):
        print("Listening for loud noises...")
        while True:
            sd.sleep(int(DURATION * 1000))