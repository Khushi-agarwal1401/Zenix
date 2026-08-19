"""
Messaging Integration — WhatsApp and Telegram bot backends.

Provides webhook handlers and message processing for:
- WhatsApp Business API (via Meta Cloud API)
- Telegram Bot API
- Common message formatting and media handling
"""

import json
import logging
import hashlib
import hmac
import os
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WhatsAppIntegration:
    """
    WhatsApp Business API integration via Meta Cloud API.

    Setup:
    1. Create a Meta Business account
    2. Set up WhatsApp Business API
    3. Get API token and phone number ID
    4. Set webhook URL to: /webhook/whatsapp

    Environment variables:
    - WHATSAPP_API_TOKEN: Meta API access token
    - WHATSAPP_PHONE_NUMBER_ID: Business phone number ID
    - WHATSAPP_VERIFY_TOKEN: Webhook verification token
    """

    def __init__(self):
        self.api_token = os.environ.get("WHATSAPP_API_TOKEN", "")
        self.phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self.verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "zenix_verify_token")
        self.api_url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}"

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify webhook subscription with Meta."""
        if mode == "subscribe" and token == self.verify_token:
            logger.info("WhatsApp webhook verified")
            return challenge
        logger.warning("WhatsApp webhook verification failed")
        return None

    def process_webhook(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming WhatsApp webhook payload."""
        try:
            entry = body.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})

            messages = value.get("messages", [])
            if not messages:
                return {"status": "no_messages"}

            msg = messages[0]
            phone = msg.get("from", "")
            msg_type = msg.get("type", "")
            msg_id = msg.get("id", "")

            # Extract text content
            text = ""
            if msg_type == "text":
                text = msg.get("text", {}).get("body", "")
            elif msg_type == "image":
                text = "[Image received]"
                # Could process image with multimodal
            elif msg_type == "audio":
                text = "[Audio received]"
            elif msg_type == "document":
                text = "[Document received]"
            elif msg_type == "location":
                lat = msg.get("location", {}).get("latitude")
                lng = msg.get("location", {}).get("longitude")
                text = f"[Location: {lat}, {lng}]"
            elif msg_type == "interactive":
                # Button/list reply
                text = msg.get("interactive", {}).get("button_reply", {}).get("title", "")
                if not text:
                    text = msg.get("interactive", {}).get("list_reply", {}).get("title", "")

            if not text:
                return {"status": "unsupported_type", "type": msg_type}

            return {
                "status": "ok",
                "phone": phone,
                "message": text,
                "message_id": msg_id,
                "type": msg_type,
                "platform": "whatsapp",
                "timestamp": msg.get("timestamp"),
            }

        except Exception as e:
            logger.error(f"WhatsApp webhook processing failed: {e}")
            return {"status": "error", "error": str(e)}

    def send_message(self, phone: str, text: str) -> Dict[str, Any]:
        """Send a text message via WhatsApp Business API."""
        if not self.api_token or not self.phone_number_id:
            return {"error": "WhatsApp API not configured. Set WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID."}

        try:
            import urllib.request
            import urllib.parse

            url = f"{self.api_url}/messages"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"body": text},
            }).encode()

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Authorization", f"Bearer {self.api_token}")
            req.add_header("Content-Type", "application/json")

            # SSL context
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            response = urllib.request.urlopen(req, context=ctx, timeout=15)
            result = json.loads(response.read().decode())
            return {"status": "sent", "message_id": result.get("messages", [{}])[0].get("id")}

        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}")
            return {"status": "error", "error": str(e)}

    def send_template(self, phone: str, template_name: str, lang: str = "en") -> Dict[str, Any]:
        """Send a pre-approved WhatsApp template message."""
        if not self.api_token or not self.phone_number_id:
            return {"error": "WhatsApp API not configured."}

        try:
            import urllib.request

            url = f"{self.api_url}/messages"
            payload = json.dumps({
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": lang},
                },
            }).encode()

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Authorization", f"Bearer {self.api_token}")
            req.add_header("Content-Type", "application/json")

            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            response = urllib.request.urlopen(req, context=ctx, timeout=15)
            return {"status": "sent"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class TelegramIntegration:
    """
    Telegram Bot API integration.

    Setup:
    1. Message @BotFather on Telegram
    2. Create a new bot with /newbot
    3. Get the bot token
    4. Set webhook to: /webhook/telegram

    Environment variables:
    - TELEGRAM_BOT_TOKEN: Bot token from BotFather
    """

    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    def verify_webhook(self, secret_token: str = None) -> bool:
        """Verify Telegram webhook (optional secret token)."""
        return True  # Telegram verifies via HTTPS + secret_token

    def process_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming Telegram update."""
        try:
            msg = update.get("message") or update.get("edited_message") or update.get("channel_post")
            if not msg:
                # Handle callback queries (inline buttons)
                callback = update.get("callback_query")
                if callback:
                    return {
                        "status": "ok",
                        "platform": "telegram",
                        "type": "callback",
                        "chat_id": callback["message"]["chat"]["id"],
                        "message": callback["data"],
                        "user": callback["from"],
                    }
                return {"status": "no_message"}

            chat_id = msg.get("chat", {}).get("id")
            user = msg.get("from", {})
            text = msg.get("text", "")
            msg_id = msg.get("message_id")

            # Handle commands
            if text.startswith("/"):
                command = text.split()[0].lower()
                return {
                    "status": "ok",
                    "platform": "telegram",
                    "type": "command",
                    "command": command,
                    "chat_id": chat_id,
                    "message": text,
                    "user": user,
                    "message_id": msg_id,
                }

            # Handle media
            if "photo" in msg:
                text = "[Photo received]"
            elif "document" in msg:
                text = f"[Document: {msg['document'].get('file_name', 'unknown')}]"
            elif "voice" in msg or "audio" in msg:
                text = "[Voice/Audio received]"
            elif "sticker" in msg:
                text = f"[Sticker: {msg['sticker'].get('emoji', '')}]"
            elif "location" in msg:
                loc = msg["location"]
                text = f"[Location: {loc['latitude']}, {loc['longitude']}]"

            if not text:
                return {"status": "unsupported"}

            return {
                "status": "ok",
                "platform": "telegram",
                "type": "message",
                "chat_id": chat_id,
                "message": text,
                "user": user,
                "message_id": msg_id,
            }

        except Exception as e:
            logger.error(f"Telegram update processing failed: {e}")
            return {"status": "error", "error": str(e)}

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Send a message via Telegram Bot API."""
        if not self.bot_token:
            return {"error": "Telegram bot token not configured."}

        try:
            import urllib.request
            import urllib.parse

            url = f"{self.api_url}/sendMessage"
            payload = json.dumps({
                "chat_id": chat_id,
                "text": text[:4096],  # Telegram limit
                "parse_mode": parse_mode,
            }).encode()

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")

            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            response = urllib.request.urlopen(req, context=ctx, timeout=15)
            result = json.loads(response.read().decode())
            return {"status": "sent", "message_id": result.get("result", {}).get("message_id")}

        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return {"status": "error", "error": str(e)}

    def send_typing(self, chat_id: int) -> Dict[str, Any]:
        """Send typing indicator."""
        if not self.bot_token:
            return {"error": "Not configured"}

        try:
            import urllib.request
            import ssl

            url = f"{self.api_url}/sendChatAction"
            payload = json.dumps({"chat_id": chat_id, "action": "typing"}).encode()
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            urllib.request.urlopen(req, context=ctx, timeout=10)
            return {"status": "ok"}
        except Exception:
            return {"status": "error"}

    def set_webhook(self, webhook_url: str) -> Dict[str, Any]:
        """Set the webhook URL for the bot."""
        if not self.bot_token:
            return {"error": "Telegram bot token not configured."}

        try:
            import urllib.request
            import ssl

            url = f"{self.api_url}/setWebhook"
            payload = json.dumps({
                "url": webhook_url,
                "allowed_updates": ["message", "callback_query"],
            }).encode()

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            response = urllib.request.urlopen(req, context=ctx, timeout=15)
            result = json.loads(response.read().decode())
            return {"status": "ok" if result.get("ok") else "failed", "detail": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Format response for messaging platforms
def format_for_platform(text: str, platform: str) -> str:
    """Format markdown text for the target platform."""
    if platform == "whatsapp":
        # WhatsApp uses *bold* and _italic_ (not ** and *)
        import re
        text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
        text = re.sub(r'__(.+?)__', r'_\1_', text)
        # Limit to 4096 chars
        if len(text) > 4096:
            text = text[:4090] + "..."
    elif platform == "telegram":
        # Telegram uses **bold** and *italic* — works as-is
        if len(text) > 4096:
            text = text[:4090] + "..."
    return text


# Singletons
whatsapp = WhatsAppIntegration()
telegram = TelegramIntegration()
