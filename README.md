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
over HTTPS. Connect this repository to Render and create a Blueprint from the
repo. In the Render dashboard, enter `GROQ_API_KEY` as a secret for the
`cura-assistant-api` service; do not commit or distribute it. After deployment,
Render provides the service's HTTPS URL. Set `CURA_API_URL` to that URL in the
CURA desktop build/distribution. Users then share the endpoint and do not need
a Groq key of their own. The app sends chat requests to `/assistant/chat`.

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

## Tests

Run the regression tests from the repository root:

```powershell
python -m unittest discover -s tests -v
```

## Current limitations

Sound detection is based on microphone signal levels and may need threshold
tuning for the device and environment. It is not a validated emergency
detection service. The “I need help” action currently displays guidance; it
does not send a message to emergency contacts or contact emergency services.
