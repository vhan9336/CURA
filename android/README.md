# CURA Android native bridge

This local Flet extension targets Flet `0.86.4` and Android. It adds:

- A microphone `AudioRecord` foreground service with a persistent notification, a dBFS meter, and loud-sound alerts.
- Hourly local check-in notifications restored after Android reboot, based on local wake/bed wall-clock times.

## Install and include

From the repository root, install the extension into the same Python environment used by Flet:

```powershell
python -m pip install -e .\android\flet_cura_android
```

For reproducible `flet build android` builds, declare this local package as a project dependency in the Flet app's dependency manifest (for example, a local project dependency pointing at `android/flet_cura_android`). This repository currently has only `requirements.txt`; do not expect an editable install in a developer environment to be available in a separate clean build environment.

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
notification refreshes with the current RMS level. Loud-sound detection uses
the same RMS/peak thresholds as the desktop detector. While CURA is open, a
detected sound routes to its dedicated sound-alert screen; if CURA is
backgrounded, Android posts a separate alert notification and the app routes
to the alert screen after it is reopened and the user signs in.

Open CURA after a device restart to resume microphone monitoring. Android
doesn't permit the app to start a microphone foreground service from the
background.

## Verification limits

Hourly notifications use Android's inexact alarms and may be delayed by Doze.
The Android build can be validated with `flet build apk`; device behavior still
needs testing on a physical phone or emulator.
