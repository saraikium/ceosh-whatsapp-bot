# WhatsApp Bot for Health & Safety Certification School

AI-powered WhatsApp bot that answers student queries about courses, certifications, schedules, and enrollment. Built with FastAPI, Pydantic AI, and Gemini 2.0 Flash via OpenRouter.

If the bot can't answer a question from the knowledge base, it tells the student a human will follow up.

## Prerequisites

- Python 3.11+
- A [Meta Developer](https://developers.facebook.com/) account with a WhatsApp Business app
- An [OpenRouter](https://openrouter.ai/) API key

## Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd whatsapp-bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in all four values:

| Variable | Where to get it |
|---|---|
| `VERIFY_TOKEN` | Make up any random string (e.g. `mysecrettoken123`) — you'll use this same string when configuring the webhook in Meta |
| `WHATSAPP_ACCESS_TOKEN` | Meta App Dashboard → WhatsApp → API Setup → generate a permanent System User token |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta App Dashboard → WhatsApp → API Setup → Phone number ID (numeric) |
| `OPENROUTER_API_KEY` | [OpenRouter](https://openrouter.ai/keys) → Create API key |

### 3. Add your school's knowledge base

Open `context.txt` and paste all relevant school information — courses, schedules, pricing, FAQs, contact details, etc. The entire file is loaded into the AI's system prompt so it can answer questions.

### 4. Run locally

```bash
uvicorn main:app --reload --port 8000
```

Test the health check:

```bash
curl http://localhost:8000/
```

Test webhook verification:

```bash
curl "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test123"
# Should return: test123
```

### 5. Expose locally with ngrok (for testing)

```bash
ngrok http 8000
```

Copy the HTTPS URL ngrok gives you (e.g. `https://abc123.ngrok-free.app`).

### 6. Configure Meta webhook

1. Go to your [Meta App Dashboard](https://developers.facebook.com/apps/)
2. Navigate to **WhatsApp → Configuration**
3. Under **Webhook**, click **Edit**
4. Set **Callback URL** to `https://your-url/webhook`
5. Set **Verify token** to the same value as your `VERIFY_TOKEN` env var
6. Click **Verify and save**
7. Subscribe to the **messages** webhook field

## Deploy to Railway

### Option A: Connect GitHub repo (recommended)

1. Push this repo to GitHub
2. Go to [railway.app](https://railway.app/) → New Project → Deploy from GitHub repo
3. Add the four environment variables in Railway's dashboard (Settings → Variables)
4. Railway auto-detects the `Procfile` and deploys
5. Go to Settings → Networking → Generate Domain to get your public URL
6. Update your Meta webhook URL to `https://your-app.up.railway.app/webhook`

### Option B: Railway CLI

```bash
npm i -g @railway/cli
railway login
railway init
railway up
```

Then add env vars via `railway variables set KEY=VALUE` or in the dashboard.

## Project Structure

```
whatsapp-bot/
├── main.py           # FastAPI webhook server (GET & POST /webhook)
├── agent.py          # Pydantic AI agent with Gemini 2.0 Flash via OpenRouter
├── context.txt       # School knowledge base (you fill this in)
├── requirements.txt  # Python dependencies
├── pyproject.toml    # Ruff linter/formatter config
├── Procfile          # Railway deployment command
├── .env.example      # Template for environment variables
└── .gitignore
```

## Development

### Linting and formatting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting (120 char line length).

```bash
pip install ruff

# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

## How It Works

1. A student sends a WhatsApp message
2. Meta's servers POST the message to your `/webhook` endpoint
3. The bot extracts the message text and sends it to Gemini 2.0 Flash (via OpenRouter) with the school's context
4. The model generates a response based solely on `context.txt`
5. The bot sends the reply back via the WhatsApp Cloud API
6. If the AI can't find an answer in the context, it tells the student a human will follow up
7. If anything errors out, the bot sends a fallback message

## Notes

- Each message is handled independently (no conversation history). This keeps things simple and stateless.
- No database is required.
- The entire `context.txt` is stuffed into the system prompt. Keep it under ~5k words for best results.
- You can swap the model by changing the model string in `agent.py` to any [OpenRouter model](https://openrouter.ai/models).
