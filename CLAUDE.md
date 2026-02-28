# CLAUDE.md

## Project Overview

WhatsApp bot for CEOSH (a health & safety certification school). Students text the school's WhatsApp Business number with queries about courses, certifications, schedules, enrollment, etc. The bot auto-answers from a knowledge base. If it can't answer, it tells the student a human will follow up within 24 business hours and notifies the team.

## Architecture

- **Python + FastAPI** — webhook server for Meta WhatsApp Cloud API
- **Pydantic AI + Gemini 2.0 Flash via OpenRouter** — AI agent
- **System prompt stuffing** — entire school knowledge base loaded from `context.txt` into the system prompt (no RAG, no vector DB)
- **Stateless** — no database, no conversation history, each message handled independently
- **Deploy target** — Railway (Procfile-based)

## Key Files

- `main.py` — FastAPI app: webhook verification (GET /webhook), message handling (POST /webhook), admin commands, handoff notifications
- `agent.py` — Pydantic AI agent with system prompt containing the school knowledge base
- `context.txt` — school knowledge base (pasted by the client)
- `pyproject.toml` — Ruff config (line length 120)

## How the Bot Works

1. Students text the school's existing WhatsApp Business number
2. The bot and the team share the same number — the bot auto-replies, the team can reply manually from the WhatsApp Business app
3. When the bot can't answer, it replies with a handoff message ("24 business hours") AND sends a WhatsApp notification to the team member's personal number (`NOTIFICATION_PHONE_NUMBER`) with the student's phone and question
4. Admins can `/pause <number>` to silence the bot for a specific student, `/resume <number>` to re-enable, `/status` to list paused numbers
5. Paused numbers are in-memory (reset on restart)

## Handoff Detection

The bot detects a handoff by checking if the AI response contains the phrase "24 business hours" (`HANDOFF_MARKER` in main.py). The system prompt instructs the AI to use this exact phrase when it can't answer.

## Environment Variables

- `VERIFY_TOKEN` — webhook verification token (shared with Meta)
- `WHATSAPP_ACCESS_TOKEN` — Meta system user permanent token
- `WHATSAPP_PHONE_NUMBER_ID` — from Meta App Dashboard
- `OPENROUTER_API_KEY` — OpenRouter API key
- `ADMIN_PHONE_NUMBERS` — comma-separated admin WhatsApp numbers (international format, no +)
- `NOTIFICATION_PHONE_NUMBER` — team member's personal number for handoff alerts (must NOT be the business number)

## Development

- Linter/formatter: Ruff, 120 char line length
- Run: `ruff check .` and `ruff format .`
- Local dev: `uvicorn main:app --reload --port 8000`
- Virtual env: `.venv/`
