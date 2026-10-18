# CURA

CURA is a desktop safety companion with scheduled check-ins, loud-noise alerts,
emergency contact details, and an optional digital helper.

## Setup

Use Python 3.10 or newer. From the repository root, install the project
dependencies and start the Flet app:

```powershell
python -m pip install -r requirements.txt
python -m src.ui
```

Allow microphone access when prompted. The app listens through the default
input device while it is running.

## How it works

- Create an account, sign in, and set wake-up and bedtime times.
- Routine check-ins are prompted about once per hour during the configured
  waking window. Overnight schedules are supported.
- Loud sound detection opens a separate sound-alert screen; scheduled check-ins
  use the routine check-up screen.
- Account details, schedule times, and preferences are stored locally in
  `%LOCALAPPDATA%\CURA\users.json` on Windows. On other systems, the default
  location is `~/.local/share/CURA/users.json`.
- The digital helper calls CURA's shared Flask API. The Groq API key belongs
  only on the API server; desktop clients must not be given this secret.

## Shared AI service

The `render.yaml` Blueprint config deploys `src/app.py` as a Flask WSGI service
over HTTPS at `https://cura-assistant-api.onrender.com`. In the Render
dashboard, enter `GROQ_API_KEY` as a secret for the `cura-assistant-api`
service; do not commit or distribute it. The desktop app defaults to this
shared endpoint, so distributed builds do not need a separate `CURA_API_URL`
setting. Set `CURA_API_URL` only to override the endpoint, such as when testing
against a local API. Users then share the endpoint and do not need a Groq key
of their own. The app sends chat requests to `/assistant/chat`.

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
flet build apk --output dist --yes
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
