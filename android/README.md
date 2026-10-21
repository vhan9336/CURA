# CURA Android native bridge

This local Flet extension targets Flet `0.86.5` and Android. It adds:

- A microphone `AudioRecord` foreground service with a persistent notification, a dBFS meter, and loud-sound alerts.
- Hourly local check-in notifications restored after Android reboot, based on local wake/bed wall-clock times.
- A permission-gated SMS sender for user-triggered help alerts to the saved emergency contacts.

## Install and include

From the repository root, install the extension into the same Python environment used by Flet:

```powershell
python -m pip install -e .\android\flet_cura_android
```

The root `pyproject.toml` declares this local package as an Android build dependency and points Flet to its source under `android/flet_cura_android`. Build from the repository root so Flet can package the native extension:

```powershell
flet build apk --output dist --yes
```

An editable install is useful for local Python development, but does not by itself include the Flutter extension in a separate build environment.

The extension's Flutter and Android files are packaged with the Python distribution and are discovered by Flet's extension build. The prebuilt Flet client used by plain `flet run` does not contain this extension; use `flet debug android` or `flet build android` with the extension installed/included.

## Python API

```python
from datetime import time
from flet_cura_android import CuraAndroid

native = CuraAndroid()  # create once in the Flet page context
permissions = await native.request_permissions()
if permissions.microphone and permissions.notifications:
    await native.start_monitoring()  # call while the app is foregrounded

schedule = await native.schedule_checkins(time(7, 0), time(22, 0))
# schedule.accuracy is "inexact"; Android may defer a check-in, especially in Doze.
dbfs = await native.microphone_level_dbfs()
await native.cancel_checkins()
await native.stop_monitoring()
```

Call `schedule_checkins(wake, bed)` again whenever the user's schedule changes. Equal wake and bed values disable the schedule. Overnight schedules (for example 22:00–07:00) are supported. Check-in alarms are inexact by design: the extension does not request special exact-alarm access and reports that Android may delay delivery. Notifications require the user to grant notification permission on Android 13+; microphone monitoring requires runtime microphone permission. The microphone service starts only while CURA's activity is visible.

Audio remains on-device; no samples are stored or transmitted. The foreground
notification refreshes with the current dBFS level. Android uses the bundled
TensorFlow Lite YAMNet model (AudioSet labels) to classify overlapping 0.975 s
audio windows, combined with a rolling noise-floor estimate and short 10 ms
impact checks. Bang/crash labels are gated by transient evidence (with a
strong-classification fallback); scream/shout/yell labels use temporal
smoothing plus an energy gate. Capture requests the unprocessed source when the
device advertises it, otherwise voice recognition, and attempts to disable
session AGC/noise suppression. Android may ignore these requests or apply
different microphone processing, so this reduces common sources of variation
but cannot make sensitivity identical across devices.

This is a starting detector, not a guarantee of recognizing every emergency.
The thresholds and model need evaluation with representative room recordings
on each target phone; measure recall per event type, false alerts per device
hour, and detection delay before relying on it. YAMNet was trained on general
AudioSet audio and is not a dedicated emergency detector. Model source and
class labels: [TensorFlow YAMNet](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet)
and [YAMNet class map](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv).
While CURA is open, a detected sound routes to its dedicated sound-alert
screen; if CURA is backgrounded, Android posts a separate alert notification
and the app routes to the alert screen after it is reopened and the user signs
in.

Open CURA after a device restart to resume microphone monitoring. Android
doesn't permit the app to start a microphone foreground service from the
background.

## Verification limits

Hourly notifications use Android's inexact alarms and may be delayed by Doze.
The Android build can be validated with `flet build apk`; device behavior still
needs testing on a physical phone or emulator.
