import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request, Response

from agent import get_response

load_dotenv()

VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
ACCESS_TOKEN = os.environ["WHATSAPP_ACCESS_TOKEN"]
PHONE_NUMBER_ID = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
ADMIN_PHONES = {n.strip() for n in os.environ.get("ADMIN_PHONE_NUMBERS", "").split(",") if n.strip()}
NOTIFICATION_PHONE = os.environ.get("NOTIFICATION_PHONE_NUMBER", "")
API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

HANDOFF_MARKER = "24 business hours"
FALLBACK_REPLY = "Sorry, I'm having trouble right now. Our team will reach out to you within 24 business hours."

# Students the bot is paused for (admin took over). In-memory — resets on restart.
paused_numbers: set[str] = set()

log = logging.getLogger("whatsapp-bot")

app = FastAPI()


@app.get("/")
async def health():
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)


async def handle_admin_command(sender: str, text: str) -> bool:
    """Handle /pause and /resume commands from admin numbers. Returns True if handled."""
    if sender not in ADMIN_PHONES:
        return False

    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower()

    if command == "/pause" and len(parts) == 2:
        number = parts[1].strip()
        paused_numbers.add(number)
        await send_message(sender, f"Bot paused for {number}. Send /resume {number} to re-enable.")
        log.info("Admin %s paused bot for %s", sender, number)
        return True

    if command == "/resume" and len(parts) == 2:
        number = parts[1].strip()
        paused_numbers.discard(number)
        await send_message(sender, f"Bot resumed for {number}.")
        log.info("Admin %s resumed bot for %s", sender, number)
        return True

    if command == "/status":
        if paused_numbers:
            msg = "Bot is paused for:\n" + "\n".join(sorted(paused_numbers))
        else:
            msg = "Bot is active for all numbers."
        await send_message(sender, msg)
        return True

    return False


async def notify_admin(student_phone: str, student_message: str):
    """Notify admin when the bot can't answer a question."""
    if not NOTIFICATION_PHONE:
        return
    notification = (
        f"Student needs help:\n"
        f"Phone: {student_phone}\n"
        f"Message: {student_message}\n\n"
        f"Reply to them from the WhatsApp Business app.\n"
        f"Send /pause {student_phone} here to pause the bot for this student."
    )
    await send_message(NOTIFICATION_PHONE, notification)


@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()

    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for message in messages:
                if message.get("type") != "text":
                    continue

                sender = message["from"]
                text = message["text"]["body"]
                message_id = message["id"]

                log.info("Message from %s: %s", sender, text)

                # Handle admin commands
                if await handle_admin_command(sender, text):
                    await mark_as_read(message_id)
                    continue

                # Skip bot reply if paused for this student
                if sender in paused_numbers:
                    log.info("Bot paused for %s, skipping", sender)
                    await mark_as_read(message_id)
                    continue

                try:
                    reply = await get_response(text)
                except Exception:
                    log.exception("AI agent failed")
                    reply = FALLBACK_REPLY

                await send_message(sender, reply)
                await mark_as_read(message_id)

                # Notify admin if the bot couldn't answer
                if HANDOFF_MARKER in reply:
                    await notify_admin(sender, text)

    return {"status": "ok"}


async def send_message(to: str, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text},
            },
            timeout=30,
        )


async def mark_as_read(message_id: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            API_URL,
            headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
            },
            timeout=10,
        )
