#!/usr/bin/env python3
"""Gmail checker — читает непрочитанные письма и отправляет сводку в Telegram"""

import imaplib
import email
import json
import os
import requests
import anthropic
from email.header import decode_header
from datetime import datetime, timezone
import zipfile
import io

# Конфиг
GMAIL_USER = "smusevmikhail@gmail.com"
GMAIL_PASS = "erad nlmc yntc jnoq"
# TG отправка убрана — используем OpenClaw cron delivery

STATE_FILE = "/home/clawd/email-checker/state.json"
ANTHROPIC_KEY = "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"
MAX_EMAILS = 20  # Максимум писем за раз

def decode_str(s):
    if not s:
        return ""
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += part
    return result

def get_text_from_msg(msg):
    """Извлекает текст и вложения из письма"""
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
                    # ZIP — распаковываем
                    if fname.lower().endswith(".zip") and payload:
                        try:
                            with zipfile.ZipFile(io.BytesIO(payload)) as zf:
                                for name in zf.namelist():
                                    with zf.open(name) as f:
                                        content = f.read(4096).decode("utf-8", errors="replace")
                                        attachments.append(f"[ZIP/{name}]: {content[:500]}")
                        except:
                            attachments.append(f"[{fname}]: не удалось прочитать")
                    elif fname.lower().endswith((".txt", ".csv", ".html")):
                        try:
                            attachments.append(f"[{fname}]: {payload.decode('utf-8', errors='replace')[:500]}")
                        except:
                            pass
                    else:
                        attachments.append(f"[вложение: {fname}]")
            elif ct == "text/plain" and "attachment" not in cd:
                try:
                    body += part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )[:1000]
                except:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )[:1000]
        except:
            pass

    return body.strip(), attachments

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_uid": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=15
    )

def summarize_emails(emails_data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    prompt = "Сделай краткую сводку этих писем на русском. Выдели важные, срочные и спам. Формат: короткий список.\n\n"
    for e in emails_data:
        prompt += f"От: {e['from']}\nТема: {e['subject']}\nТекст: {e['body'][:300]}\n"
        if e['attachments']:
            prompt += f"Вложения: {', '.join(e['attachments'][:3])}\n"
        prompt += "---\n"

    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text

def main():
    state = load_state()
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select("INBOX")

    # Ищем непрочитанные
    status, data = mail.search(None, "UNSEEN")
    uids = data[0].split()

    if not uids:
        send_telegram("📬 Новых писем нет.")
        mail.logout()
        return

    # Берём последние MAX_EMAILS
    uids = uids[-MAX_EMAILS:]
    emails_data = []

    for uid in uids:
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != "OK":
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_str(msg.get("Subject", "(без темы)"))
        sender  = decode_str(msg.get("From", ""))
        date    = msg.get("Date", "")
        body, attachments = get_text_from_msg(msg)
        emails_data.append({
            "from": sender[:80],
            "subject": subject[:100],
            "date": date[:30],
            "body": body,
            "attachments": attachments
        })

    mail.logout()

    # Сводка через Claude
    summary = summarize_emails(emails_data)
    count = len(uids)
    text = f"📧 <b>Почта smusevmikhail@gmail.com</b>\n{count} новых писем\n\n{summary}"
    send_telegram(text)
    save_state({"last_uid": int(uids[-1]), "checked_at": datetime.now(timezone.utc).isoformat()})

if __name__ == "__main__":
    main()
