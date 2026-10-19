# audio.py
from collections.abc import Callable
import threading

import flet as ft

RMS_THRESHOLD = 0.04
PEAK_THRESHOLD = 0.65
PEAK_MIN_RMS = 0.018
RESET_THRESHOLD = 0.015
DURATION = 0.1
SAMPLE_RATE = 44100


def _audio_levels(indata) -> tuple[float, float]:
    import numpy as np

    samples = np.asarray(indata, dtype=np.float32)
    if samples.size == 0:
        return 0.0, 0.0
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    peak = float(np.max(np.abs(samples)))
    return rms, peak


def _should_trigger_audio_alert(
    rms: float, peak: float, alert_active: bool
) -> bool:
    if alert_active:
        return False
    return rms >= RMS_THRESHOLD or (
        peak >= PEAK_THRESHOLD and rms >= PEAK_MIN_RMS
    )


def _dispatch_audio_alert(page: ft.Page, callback: Callable[[], None]) -> None:
    async def show_audio_alert():
        callback()

    page.run_task(show_audio_alert)


def start_listening(
    page: ft.Page,
    audio_alert_callback: Callable[[], None],
    stop_event: threading.Event | None = None,
):
    import sounddevice as sd

    if stop_event is None:
        stop_event = threading.Event()
    alert_active = False

    def audio_callback(indata, frames, time_info, status):
        nonlocal alert_active
        if stop_event.is_set():
            return
        if status:
            print(status)

        rms, peak = _audio_levels(indata)
        if _should_trigger_audio_alert(rms, peak, alert_active):
            alert_active = True
            print(
                f"\033[31mAudio system triggered! "
                f"RMS: {rms:.3f}, peak: {peak:.3f}\033[0m"
            )
            _dispatch_audio_alert(page, audio_alert_callback)
        elif alert_active and rms <= RESET_THRESHOLD:
            alert_active = False

    with sd.InputStream(
        callback=audio_callback, channels=1, samplerate=SAMPLE_RATE
    ):
        print("Listening for loud noises...")
        while not stop_event.is_set():
            sd.sleep(int(DURATION * 1000))