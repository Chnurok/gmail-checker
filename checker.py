#!/usr/bin/env python3
"""Gmail checker — reads unread emails and sends a summarized digest to Telegram."""

import email
import imaplib
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from email.header import decode_header

import anthropic
import requests

GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "250504825")
STATE_FILE = os.environ.get("STATE_FILE", "./state.json")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MAX_EMAILS = int(os.environ.get("MAX_EMAILS", "20"))


def decode_str(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += part
    return result


def get_text_from_msg(msg):
    """Extract text and a compact view of attachments from an email message."""
    body = ""
    attachments = []

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))

            if "attachment" in cd:
                fname = part.get_filename()
                if fname:
                    fname = decode_str(fname)
                    payload = part.get_payload(decode=True)
                    if fname.lower().endswith(".zip") and payload:
                        try:
                            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                                for name in zf.namelist():
                                    with zf.open(name) as f:
                                        content = f.read(4096).decode("utf-8", errors="replace")
                                        attachments.append(f"[ZIP/{name}]: {content[:500]}")
                        except Exception:
                            attachments.append(f"[{fname}]: unable to read")
                    elif fname.lower().endswith((".txt", ".csv", ".html")) and payload:
                        try:
                            attachments.append(f"[{fname}]: {payload.decode('utf-8', errors='replace')[:500]}")
                        except Exception:
                            pass
                    else:
                        attachments.append(f"[attachment: {fname}]")
            elif ct == "text/plain" and "attachment" not in cd:
                try:
                    body += part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )[:1000]
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )[:1000]
        except Exception:
            pass

    return body.strip(), attachments


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_uid": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f)


def send_telegram(text: str):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15,
    )


def summarize_emails(emails_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    prompt = (
        "Сделай краткую сводку этих писем на русском. "
        "Выдели важные, срочные и спам. Формат: короткий список.\n\n"
    )
    for item in emails_data:
        prompt += f"От: {item['from']}\nТема: {item['subject']}\nТекст: {item['body'][:300]}\n"
        if item["attachments"]:
            prompt += f"Вложения: {', '.join(item['attachments'][:3])}\n"
        prompt += "---\n"

    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def ensure_config():
    required = {
        "GMAIL_USER": GMAIL_USER,
        "GMAIL_APP_PASSWORD": GMAIL_PASS,
        "TELEGRAM_BOT_TOKEN": TG_TOKEN,
        "ANTHROPIC_API_KEY": ANTHROPIC_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def main():
    ensure_config()
    _state = load_state()

    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select("INBOX")

    status, data = mail.search(None, "UNSEEN")
    uids = data[0].split()

    if not uids:
        send_telegram("📬 Новых писем нет.")
        mail.logout()
        return

    uids = uids[-MAX_EMAILS:]
    emails_data = []

    for uid in uids:
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != "OK":
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_str(msg.get("Subject", "(без темы)"))
        sender = decode_str(msg.get("From", ""))
        date = msg.get("Date", "")
        body, attachments = get_text_from_msg(msg)
        emails_data.append(
            {
                "from": sender[:80],
                "subject": subject[:100],
                "date": date[:30],
                "body": body,
                "attachments": attachments,
            }
        )

    mail.logout()

    summary = summarize_emails(emails_data)
    count = len(uids)
    text = f"📧 <b>Почта {GMAIL_USER}</b>\n{count} новых писем\n\n{summary}"
    send_telegram(text)
    save_state({"last_uid": int(uids[-1]), "checked_at": datetime.now(timezone.utc).isoformat()})


if __name__ == "__main__":
    main()
