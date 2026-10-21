# CURA

CURA is a personal safety companion with scheduled check-ins, on-device
sound alerts for impacts and scream-like sounds, a private check-in calendar, emergency contact details,
and an optional digital helper.

## Setup

Use Python 3.10 or newer. From the repository root, install the project
dependencies and start the Flet app:

```powershell
python -m pip install -r requirements.txt
python -m src.ui
```

Allow microphone access when prompted. New accounts open directly into CURA
after a short feature walkthrough; setting a daily schedule is optional and can
be done later. CURA keeps you signed in on this device until you choose Log
out. Logging out stops monitoring and scheduled check-ins.

## How it works

- Create an account and start using CURA immediately, or sign in to an existing
  account. The first session includes a skippable feature walkthrough.
- Set wake-up and bedtime times from the dashboard whenever you're ready.
- Routine check-ins are prompted about once per hour during the configured
  waking window, starting one hour after sign-in and schedule setup. Overnight
  schedules are supported.
- Loud sound detection opens a dedicated sound-alert screen; scheduled
  check-ins use a separate routine check-up screen.
- The Home tab explains what each feature does. The History tab shows a
  calendar of check-ins you acknowledged, stored with your account on-device.
- Audio is analyzed locally with Google's YAMNet audio event model and short
  term level checks. CURA does not record audio or transcribe speech. The model
  can miss events or misclassify sounds, and phone microphones vary; validate
  alert behavior on the devices where CURA will be used. When a user taps “I need help” on a routine or sound
  alert, CURA requests Android SMS permission if needed, then sends the prepared
  message to the saved emergency contacts after the user taps the help button.
  The mobile carrier may charge for SMS. Automatic SMS requires the Android
  build; desktop builds cannot send SMS.
- Account details, schedule times, and preferences are stored locally in
  `%LOCALAPPDATA%\CURA\users.json` on Windows. On other systems, the default
  location is `~/.local/share/CURA/users.json`.
- On Android, account data is stored under CURA's writable app data directory.
- Replace `src/assets/logo-light.png` and `src/assets/logo-dark.png` with your
  light-background and dark-background logo images. The app uses the matching
  image for in-app branding. `src/assets/icon_android.png` is the Android
  launcher icon source; rebuild the APK after changing it.
- CURA follows the device's system light/dark appearance.
- The digital helper calls CURA's shared Flask API. The Groq API key belongs
  only on the API server; desktop clients must not be given this secret.

## Shared AI service

The `render.yaml` Blueprint config deploys `src/app.py` as a Flask WSGI service
over HTTPS at `https://cura-assistant-api.onrender.com`. In the Render
dashboard, enter `GROQ_API_KEY` as a secret/environment value for the
`cura-assistant-api` service; never commit or distribute credentials. The desktop app defaults to this
shared endpoint, so distributed builds do not need a separate `CURA_API_URL`
setting. Set `CURA_API_URL` only to override the endpoint, such as when testing
against a local API. Users then share the endpoint and do not need a Groq key
of their own. The app sends chat requests to `/assistant/chat`. Help messages
use Android's SMS app and do not use the shared API.

Emergency contact numbers must use international E.164 format, including the
leading `+` and country code (for example, `+14155550123`). Users can edit both
numbers under Settings.

For local development, install API dependencies with
`python -m pip install -r requirements-api.txt`. Run the API and desktop app in
separate PowerShell
terminals:

```powershell
# API terminal (set a real key locally; never commit it)
$env:GROQ_API_KEY = "your-groq-key"
python -m src.app
```

```powershell
# Desktop terminal
$env:CURA_API_URL = "http://127.0.0.1:5001"
python -m src.ui
```

The chat endpoint limits request sizes and allows at most 10 requests per
client IP per minute per server process. For a multi-worker or public
deployment, also enable provider spending limits and a shared rate limiter at
the hosting platform or gateway.

## Android APK

Build a sideloadable Android APK from the repository root with:

```powershell
flet build apk --output dist --yes --android-adaptive-icon-background "#0C5B52"
```

The first build installs the Flutter and Android build tools if they are
missing. Flet reads Android-specific dependencies and app settings from
`pyproject.toml`; the native microphone/notification bridge is in
`android/flet_cura_android`.

On first use, grant CURA microphone and notification permissions. While
monitoring is enabled, Android shows an ongoing notification for microphone
access. Loud sounds trigger a separate sound-alert notification/screen.
Scheduled check-ins use Android local notifications and follow the configured
wake/bed window, including overnight schedules. Android may defer these
notifications while the device is in Doze mode; they are not guaranteed to
arrive exactly on the hour. Reopen CURA after a device restart to resume
microphone monitoring.

## Tests

Run the regression tests from the repository root:

```powershell
python -m unittest discover -s tests -v
```
