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
API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"

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

                try:
                    reply = await get_response(text)
                except Exception:
                    log.exception("AI agent failed")
                    reply = "Sorry, I'm having trouble right now. Our team will get back to you shortly."

                await send_message(sender, reply)
                await mark_as_read(message_id)

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
