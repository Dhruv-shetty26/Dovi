# 🤖 Dovi V1 — Your AI Desktop Companion

Dovi is a small, friendly AI desktop companion that can:

- Have natural conversations
- Set timers
- Play/control music
- Set reminders
- Open whitelisted applications
- Speak responses aloud
- Display a cute animated avatar

## Quick Start

### 1. Prerequisites

- Python 3.11+ (you have 3.12 ✓)
- A terminal (VS Code terminal works great)

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys (not needed for Phase 0).

### 5. Run Dovi

```bash
python run.py
```

You should see Dovi's startup banner with a status check of all subsystems.

## Project Structure

```
DOVI/
├── app/              # Application source code
│   ├── agent/        # AI agent (LLM, prompts, memory)
│   ├── tools/        # Tool implementations (timer, music, etc.)
│   ├── voice/        # Speech-to-text and text-to-speech
│   ├── avatar/       # Avatar states and rendering
│   ├── ui/           # Desktop user interface
│   └── config/       # Settings and configuration
├── assets/           # Avatar images, sounds
├── data/             # Runtime data (SQLite, etc.)
├── tests/            # Test suite
├── .env              # Your API keys (never commit this!)
├── .env.example      # Template for .env
├── requirements.txt  # Python dependencies
└── run.py            # Entry point: python run.py
```

## Development Phases

| Phase | Description          | Status |
|-------|----------------------|--------|
| 0     | Project setup        | ✅      |
| 1     | Text conversation    | ⬜      |
| 2     | Tool system          | ⬜      |
| 3     | Voice input (STT)    | ⬜      |
| 4     | Voice output (TTS)   | ⬜      |
| 5     | Avatar               | ⬜      |
| 6     | Full integration     | ⬜      |

## Testing

```bash
python -m pytest tests/ -v
```

## Troubleshooting

| Problem                        | Solution                                      |
|--------------------------------|-----------------------------------------------|
| `ModuleNotFoundError`          | Make sure your venv is activated               |
| `.env` keys not loading        | Check the file exists and has no trailing spaces |
| `python` not found             | Use `python3` instead                          |

## License

Personal project by Dhruv.

