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
- The digital helper is optional. Set `GROQ_API_KEY` to enable it.

## Tests

Run the regression tests from the repository root:

```powershell
python -m unittest discover -s tests -v
```
