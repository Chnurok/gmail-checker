#!/usr/bin/env python3
import imaplib, email, json, requests, anthropic
from email.header import decode_header
from datetime import datetime, timezone
import os

GMAIL_USER    = os.environ.get("GMAIL_USER", "")
GMAIL_PASS    = os.environ.get("GMAIL_APP_PASSWORD", "")
TG_TOKEN      = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "250504825")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
STATE_FILE    = os.environ.get("STATE_FILE", "./state.json")
MAX_EMAILS    = 20

def decode_str(s):
    if not s: return ""
    parts = decode_header(s)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or "utf-8", errors="replace")
        else:
            result += part
    return result

def get_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                try:
                    body += part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")[:800]
                except: pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")[:800]
        except: pass
    return body.strip()

def send_tg(text):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login(GMAIL_USER, GMAIL_PASS)
mail.select("INBOX")
status, data = mail.search(None, "UNSEEN")
uids = data[0].split()

if not uids:
    send_tg("📬 Новых писем нет.")
    mail.logout()
    exit()

uids = uids[-MAX_EMAILS:]
emails_data = []
for uid in uids:
    status, msg_data = mail.fetch(uid, "(RFC822)")
    if status != "OK": continue
    msg = email.message_from_bytes(msg_data[0][1])
    emails_data.append({
        "from": decode_str(msg.get("From",""))[:80],
        "subject": decode_str(msg.get("Subject","(без темы)"))[:100],
        "body": get_body(msg)
    })
mail.logout()

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
prompt = "Сделай краткую сводку этих писем на русском. Выдели важные, срочные и спам. Короткий список:\n\n"
for e in emails_data:
    prompt += f"От: {e['from']}\nТема: {e['subject']}\nТекст: {e['body'][:300]}\n---\n"

result = client.messages.create(model="claude-haiku-4-5", max_tokens=1024,
    messages=[{"role":"user","content":prompt}])
summary = result.content[0].text

text = f"📧 <b>Почта {GMAIL_USER}</b>\n{len(uids)} новых писем\n\n{summary}"
send_tg(text)
print("Done")
