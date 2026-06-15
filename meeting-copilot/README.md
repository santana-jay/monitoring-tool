# Background Meeting Co-pilot

A cross-platform desktop app that runs quietly in the system tray, captures
**system/loopback audio** during meetings, transcribes it locally in real time,
keeps structured notes, and surfaces **grounded, cited, confidence-gated**
reply/comment suggestions using the Anthropic Claude API.

> **Honest disclaimer about hallucination.** Zero hallucination is **not
> achievable** with any LLM, and this project does not claim it. Instead it
> minimizes hallucination structurally — through retrieval grounding, mandatory
> citations, JSON-schema validation, and confidence gating (abstain by
> default). Treat suggestions as **AI proposals, not facts**.

> **Legal / consent notice.** Recording meetings is legally regulated in many
> jurisdictions and often requires the consent of participants. You are
> responsible for complying with the law where you operate. The app shows a
> local consent reminder and a visible "recording active" indicator.

---

## What it does

- **Background tray app** — no taskbar window; a global hotkey toggles a small,
  frameless, always-on-top suggestions overlay that **never steals focus**.
- **Passive system-audio capture** — captures what *you hear* (loopback),
  independent of the meeting platform (Zoom/Teams/Meet all work). It **never
  opens your microphone, never joins the call, and never transmits audio**, so
  other participants get no indication it is running.
- **Local streaming transcription** via faster-whisper + voice-activity
  detection. Audio is processed in memory and, by default, never written to
  disk. **Only transcript text is ever sent to the AI.**
- **Live structured notes** — topics, decisions, action items, open questions —
  extracted (low temperature) from what was actually said.
- **Grounded suggestions** — built only from retrieved past/earlier transcript
  snippets plus a recent transcript window; each carries citations
  (timestamps) and a confidence score. Low-confidence items are suppressed in
  favour of an explicit *"no confident suggestion"*.
- **Local-first storage** — SQLite for transcripts, notes, and embeddings.
  Easy global **pause / stop / purge** controls.

## Architecture

```
 AudioCapture (loopback)         ── platform backends: WASAPI / sounddevice
        │  PCM frames
        ▼
 EnergyVAD ──► Transcriber (faster-whisper, pluggable)
        │  timestamped segments
        ▼
 Store (SQLite)  ◄──►  RetrievalStore (embeddings + cosine index)
        │                         │ grounded snippets + citations
        ▼                         ▼
 Engine ───► NotesPipeline (strong model, low temp, schema-validated)
        └──► SuggestionsPipeline (fast model, streaming, cited, gated)
                          │
                          ▼
        UI: tray + frameless overlay + settings  (local screen only)
```

The non-UI core (`config`, `store`, `retrieval`, `ai`, `audio` abstraction,
`engine`) is importable and unit-tested without any UI / ML / audio packages
installed. Heavy and platform-specific dependencies are imported lazily.

### Anti-hallucination design

| Mechanism | Where |
|-----------|-------|
| Grounding (only provided context is usable) | `ai/prompts.py` system prompts |
| Citations (transcript span/timestamp per item) | `core/models.py` `Citation`, surfaced in overlay |
| Schema validation (drop malformed) | `ai/grounding.py` (pydantic) |
| Citation grounding check (span overlap + verbatim quote present) | `ai/grounding.py` `GroundingContext` |
| Confidence gating + abstain-by-default | `ai/grounding.py` `validate_suggestions` |
| Separation of duties (notes = extraction, suggestions = proposals) | `ai/pipelines.py` |

## Install

Requires **Python 3.11+**.

```bash
cd meeting-copilot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .                       # core only
# Add the features you want:
pip install -e '.[ui,stt,retrieval,ai,secrets,hotkeys]'
# Audio backend (per OS):
pip install -e '.[audio]'              # macOS / Linux (PortAudio/sounddevice)
pip install -e '.[audio-windows]'      # Windows (WASAPI loopback)
```

## Configure

Copy `.env.example` to `.env` and fill it in (or set the variables in your
environment / OS keychain):

```bash
cp .env.example .env
```

- **API key:** store it in the OS keychain (preferred) via the Settings window,
  or set `ANTHROPIC_API_KEY`. It is never hardcoded and never logged.
- **Model IDs:** set `COPILOT_MODEL_FAST` (real-time suggestions) and
  `COPILOT_MODEL_STRONG` (note summarization). These are intentionally **not**
  hardcoded — **verify the current model IDs, context limits, and pricing at
  <https://docs.claude.com> before use**, because Anthropic model IDs change
  over time.

## Run

```bash
meeting-copilot           # or: python -m copilot
```

The app appears in the system tray. Use the tray menu to Start/Pause/Stop, open
Settings, toggle the overlay, or **Purge all data**. The default hotkey
`ctrl+shift+space` toggles the overlay.

## Per-OS audio loopback setup

Cross-platform loopback is the trickiest part. If loopback isn't available the
app degrades gracefully and shows these instructions instead of crashing.

### Windows (WASAPI loopback)
Install the Windows audio extra: `pip install -e '.[audio-windows]'`.
WASAPI exposes a loopback of your default output device — no extra drivers
needed. If you use multiple output devices, pick the right one in Settings.

### macOS (ScreenCaptureKit or BlackHole)
macOS does not expose system audio to apps by default. Either:
1. **ScreenCaptureKit (macOS 13+):** grant this app *Screen Recording*
   permission in System Settings → Privacy & Security → Screen Recording; or
2. **BlackHole fallback:** install [BlackHole](https://existential.audio/blackhole/),
   create a *Multi-Output Device* in Audio MIDI Setup that includes BlackHole +
   your speakers, set it as the system output, then select BlackHole as the
   capture device in Settings.

### Linux (PulseAudio / PipeWire monitor)
List monitor sources and pick the `*.monitor` for your output device:
```bash
pactl list short sources | grep monitor
```
On PipeWire systems the Pulse compatibility layer exposes the same monitor
sources. Install the audio extra: `pip install -e '.[audio]'`.

## Privacy & data boundary

- **Audio never leaves your machine.** It is processed in memory; only
  transcript *text* is sent to the Anthropic API, and only for the AI features.
- Raw audio is **not** written to disk unless you explicitly set
  `COPILOT_PERSIST_AUDIO=1` (debugging only).
- All transcripts, notes, and embeddings live in a local SQLite database under
  your per-user data directory. **Purge all data** deletes everything.
- The overlay is rendered on your local screen only and attempts to exclude
  itself from screen capture where the OS/Qt supports it.

## Packaging

The app is a standard Python package (`pyproject.toml`) exposing a
`meeting-copilot` entry point. For standalone per-OS bundles, build with
[PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller --noconsole --name MeetingCopilot -p src src/copilot/__main__.py
```

Bundle the appropriate audio backend per OS and ship the per-OS setup notes
above. (Model downloads for faster-whisper / sentence-transformers happen on
first run.)

## Development & tests

```bash
pip install -e '.[dev]'
pytest
```

Tests cover the non-UI core: the audio abstraction (mock backends), VAD
segmentation, the SQLite store, retrieval/ranking, grounding & schema
validation, the AI pipelines (mocked client), and the engine end-to-end with
fakes. No network, GPU, or audio device is required to run them.

## Limitations

- Suggestions and notes can still be wrong — they are model output. Citations
  let you verify against the transcript; always do so for anything important.
- Speaker attribution is best-effort.
- The bundled offline embedder (`HashingEmbedder`) is a dependency-free
  fallback; install the `retrieval` extra for higher-quality sentence
  embeddings.
