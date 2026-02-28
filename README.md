# WhatsApp Bot for Health & Safety Certification School

AI-powered WhatsApp bot that answers student queries about courses, certifications, schedules, and enrollment. Built with FastAPI, Pydantic AI, and Gemini 2.0 Flash via OpenRouter.

If the bot can't answer a question from the knowledge base, it tells the student a human will follow up and notifies the team.

## How Students Use It

Students text your **existing WhatsApp Business number** — the same number your team already uses. There is no separate bot number. The bot sits in front of your business number and auto-replies to incoming messages.

- **Student texts your business number** → Meta forwards it to the bot → bot replies instantly
- **Your team opens the WhatsApp Business app** → they see the same conversations and can reply manually at any time

## What Happens When the Bot Can't Answer

When a student asks something that isn't in the knowledge base:

1. **The student** receives: "I don't have that information right now. Our team will reach out to you within 24 business hours."
2. **The team member** (the `NOTIFICATION_PHONE_NUMBER`) receives a WhatsApp message from the bot:
   ```
   Student needs help:
   Phone: 923001234567
   Message: Do you offer evening classes for the NEBOSH diploma?

   Reply to them from the WhatsApp Business app.
   Send /pause 923001234567 here to pause the bot for this student.
   ```
3. The team member opens the **WhatsApp Business app**, finds the student's conversation, and replies directly.
4. If the team member wants the bot to stop auto-replying to that student while they handle it, they text `/pause 923001234567` to the bot.

**Important:** The `NOTIFICATION_PHONE_NUMBER` must be a team member's personal WhatsApp number — not the business number itself, since the bot cannot message its own number.

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

Edit `.env` and fill in the values:

| Variable | Where to get it |
|---|---|
| `VERIFY_TOKEN` | Make up any random string (e.g. `mysecrettoken123`) — you'll use this same string when configuring the webhook in Meta |
| `WHATSAPP_ACCESS_TOKEN` | Meta App Dashboard → WhatsApp → API Setup → generate a permanent System User token |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta App Dashboard → WhatsApp → API Setup → Phone number ID (numeric) |
| `OPENROUTER_API_KEY` | [OpenRouter](https://openrouter.ai/keys) → Create API key |
| `ADMIN_PHONE_NUMBERS` | Comma-separated list of admin WhatsApp numbers in international format (e.g. `923001234567,923009876543`) |
| `NOTIFICATION_PHONE_NUMBER` | The WhatsApp number that receives handoff alerts when the bot can't answer a student |

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
3. Add all environment variables in Railway's dashboard (Settings → Variables)
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

## How It Works (Technical)

1. A student sends a WhatsApp message to your business number
2. Meta's servers POST the message to your `/webhook` endpoint
3. If the sender is an admin and the message is a command (`/pause`, `/resume`, `/status`), it's handled as an admin action
4. If the bot is paused for that student, the message is marked as read but the bot does not reply (the team handles it from the WhatsApp Business app)
5. Otherwise, the bot sends the message text to Gemini 2.0 Flash (via OpenRouter) along with the school's knowledge base
6. The model generates a response based solely on `context.txt`
7. The bot sends the reply back via the WhatsApp Cloud API
8. If the response indicates a handoff (answer not in the knowledge base), the bot also sends a notification to the team member's WhatsApp with the student's number and question
9. If anything errors out, the bot sends a fallback message: "Our team will reach out to you within 24 business hours"

## Admin Commands

Admins (numbers listed in `ADMIN_PHONE_NUMBERS`) can text the bot directly to control it. These commands are sent as regular WhatsApp messages to your business number:

| Command | What it does |
|---|---|
| `/pause 923001234567` | Pause the bot for that student — the bot stops replying so you can handle the conversation from the WhatsApp Business app |
| `/resume 923001234567` | Re-enable the bot for that student |
| `/status` | List all currently paused numbers |

Phone numbers must be in international format without `+` (e.g. `923001234567`).

**Note:** Admin commands are only recognized from numbers listed in `ADMIN_PHONE_NUMBERS`. Messages from any other number are treated as student queries.

## Notes

- **One number for everything** — the bot and your team share the same WhatsApp Business number. Students text the number, the bot replies, and your team can jump in from the WhatsApp Business app whenever needed.
- **Stateless** — each message is handled independently (no conversation history). Keeps things simple.
- **No database** — paused numbers are stored in memory and reset if the server restarts.
- **Knowledge base size** — the entire `context.txt` is loaded into the system prompt. Keep it under ~5k words for best results.
- **Swap models** — change the model string in `agent.py` to any [OpenRouter model](https://openrouter.ai/models).
