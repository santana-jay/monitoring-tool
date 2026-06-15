# Running the Meeting Co-pilot locally (for your own meetings)

This is a focused, single-machine quickstart for running **only** the
`meeting-copilot` app during your own meetings. It runs entirely on your
computer: it passively listens to the audio you already hear, transcribes it
locally, and shows you private notes and suggestions on your screen.

> **It is local-only and passive.** It never joins the call, never opens your
> microphone, never transmits audio, and makes no sound. Only the person
> running it sees that it is running — the overlay and indicators are drawn on
> your screen only. Only transcript *text* (never audio) is sent to the
> Anthropic API, and only when AI features are enabled.

> **Consent & law.** Recording meetings is regulated in many places and often
> requires participant consent. You are responsible for complying with the law
> where you operate.

---

## 1. Prerequisites

- **Python 3.11+** (`python --version` to check).
- An **Anthropic API key** if you want AI notes/suggestions (optional — the app
  still captures and transcribes without it).

## 2. Install

```bash
cd meeting-copilot
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

For real meeting use you want the full feature set (tray UI, transcription,
retrieval, AI, keychain, hotkey) **plus** the audio backend for your OS:

```bash
# App features:
pip install -e '.[ui,stt,retrieval,ai,secrets,hotkeys]'

# Audio loopback backend — pick the one for your OS:
pip install -e '.[audio]'          # macOS / Linux (PortAudio/sounddevice)
pip install -e '.[audio-windows]'  # Windows (WASAPI loopback)
```

## 3. Configure

```bash
cp .env.example .env
```

Open `.env` and set, at minimum, the two model IDs if you want AI features.
**Model IDs change over time — verify the current IDs at
<https://docs.claude.com> before using them.**

```ini
COPILOT_MODEL_FAST=     # fast/low-latency model for real-time suggestions
COPILOT_MODEL_STRONG=   # stronger model for note summarization
```

For the API key, prefer storing it in your OS keychain from the Settings window
(opened from the tray). As a development fallback you may set
`ANTHROPIC_API_KEY` in `.env`. The key is never logged.

Other useful settings (all optional, defaults shown):

| Setting | Default | Purpose |
|---------|---------|---------|
| `COPILOT_WHISPER_MODEL` | `base` | Transcription model size (`tiny`…`large-v3`). Larger = more accurate, slower. |
| `COPILOT_MIN_CONFIDENCE` | `0.55` | Suggestions below this are hidden ("no confident suggestion"). |
| `COPILOT_HOTKEY` | `ctrl+shift+space` | Global hotkey to show/hide the overlay. |
| `COPILOT_DATA_DIR` | OS default | Where the local SQLite database lives. |
| `COPILOT_PERSIST_AUDIO` | `0` | Keep `0`: audio stays in memory and is never written to disk. |

## 4. Enable system-audio loopback (one-time per OS)

The app captures what you *hear*, so you must let your OS expose the system
audio. If loopback isn't available the app won't crash — it shows these same
instructions instead.

- **Windows:** install `.[audio-windows]`. WASAPI exposes a loopback of your
  default output device automatically; no extra drivers needed.
- **macOS:** grant **Screen Recording** permission (System Settings → Privacy &
  Security → Screen Recording) for ScreenCaptureKit on macOS 13+, **or** install
  [BlackHole](https://existential.audio/blackhole/) and route output through a
  Multi-Output Device.
- **Linux (PulseAudio/PipeWire):** find your output's monitor source and pick it
  in Settings:
  ```bash
  pactl list short sources | grep monitor
  ```

## 5. Run it during a meeting

```bash
meeting-copilot          # or: python -m copilot
```

The app appears in your **system tray** (no taskbar window). From there:

1. **Start** capture when your meeting begins.
2. Press the hotkey (`ctrl+shift+space` by default) to toggle the always-on-top
   suggestions **overlay**. It never steals focus from your call.
3. **Pause / Stop** from the tray when you want to stop listening.
4. **Purge all data** from the tray deletes every transcript, note, and
   embedding from the local database.

That's it — everything stays on your machine.

## 6. Verify your setup (optional)

Run the core test suite (no audio device, GPU, or network required):

```bash
pip install -e '.[dev]'
pytest
```

## Troubleshooting

- **"PySide6 is required for the desktop app"** — install the UI extra:
  `pip install -e '.[ui]'`.
- **No audio is captured** — complete the OS loopback step above and select the
  correct output/monitor device in Settings.
- **No suggestions appear** — confirm your API key is set and the model IDs in
  `.env` are valid current IDs from <https://docs.claude.com>. Low-confidence
  suggestions are intentionally suppressed.

For the full architecture, privacy boundary, and packaging details, see
[`README.md`](README.md).
