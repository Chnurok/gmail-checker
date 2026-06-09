#!/usr/bin/env python3
"""Gmail checker — reads unread emails, summarizes them, and sends a digest to Telegram."""

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
MAX_BODY_CHARS = int(os.environ.get("MAX_BODY_CHARS", "1000"))
MAX_ATTACHMENT_CHARS = int(os.environ.get("MAX_ATTACHMENT_CHARS", "500"))
SUMMARY_MODEL = os.environ.get("SUMMARY_MODEL", "claude-haiku-4-5")


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
                                        attachments.append(f"[ZIP/{name}]: {content[:MAX_ATTACHMENT_CHARS]}")
                        except Exception:
                            attachments.append(f"[{fname}]: unable to read")
                    elif fname.lower().endswith((".txt", ".csv", ".html")) and payload:
                        try:
                            attachments.append(f"[{fname}]: {payload.decode('utf-8', errors='replace')[:MAX_ATTACHMENT_CHARS]}")
                        except Exception:
                            pass
                    else:
                        attachments.append(f"[attachment: {fname}]")
            elif ct == "text/plain" and "attachment" not in cd:
                try:
                    body += part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )[:MAX_BODY_CHARS]
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace"
            )[:MAX_BODY_CHARS]
        except Exception:
            pass

    return body.strip(), attachments


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"processed_uids": [], "last_uid": 0}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def filter_new_uids(uids, state):
    processed = {str(uid) for uid in state.get("processed_uids", [])}
    last_uid = int(state.get("last_uid", 0) or 0)
    fresh = []
    for uid in uids:
        uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)
        if uid_str in processed:
            continue
        try:
            uid_num = int(uid_str)
        except ValueError:
            uid_num = 0
        if last_uid and uid_num and uid_num <= last_uid:
            continue
        fresh.append(uid)
    return fresh


def update_state_after_run(state, uids):
    processed = [str(uid.decode() if isinstance(uid, bytes) else uid) for uid in uids]
    numeric = [int(uid) for uid in processed if str(uid).isdigit()]
    merged = list(dict.fromkeys((state.get("processed_uids", []) + processed)))[-500:]
    return {
        "processed_uids": merged,
        "last_uid": max([state.get("last_uid", 0)] + numeric) if numeric else state.get("last_uid", 0),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def build_fallback_summary(emails_data):
    lines = []
    for item in emails_data:
        preview = (item.get("body") or "").replace("\n", " ").strip()
        if len(preview) > 140:
            preview = preview[:137] + "..."
        line = f"- {item['subject'] or '(без темы)'} — {item['from'] or 'неизвестный отправитель'}"
        if preview:
            line += f": {preview}"
        lines.append(line)
    return "\n".join(lines[:MAX_EMAILS])


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
        model=SUMMARY_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def ensure_config():
    required = {
        "GMAIL_USER": GMAIL_USER,
        "GMAIL_APP_PASSWORD": GMAIL_PASS,
        "TELEGRAM_BOT_TOKEN": TG_TOKEN,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def collect_emails(mail, uids):
    emails_data = []
    for uid in uids:
        status, msg_data = mail.fetch(uid, "(RFC822)")
        if status != "OK" or not msg_data or not msg_data[0]:
            continue
        msg = email.message_from_bytes(msg_data[0][1])
        subject = decode_str(msg.get("Subject", "(без темы)"))
        sender = decode_str(msg.get("From", ""))
        date = msg.get("Date", "")
        body, attachments = get_text_from_msg(msg)
        emails_data.append(
            {
                "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
                "from": sender[:80],
                "subject": subject[:100],
                "date": date[:60],
                "body": body,
                "attachments": attachments,
            }
        )
    return emails_data


def format_digest(gmail_user, emails_data, summary, used_fallback=False):
    count = len(emails_data)
    prefix = "⚠️ AI summary unavailable, using fallback digest\n\n" if used_fallback else ""
    return f"📧 <b>Почта {gmail_user}</b>\n{count} новых писем\n\n{prefix}{summary}"


def main():
    ensure_config()
    state = load_state()

    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select("INBOX")

    status, data = mail.search(None, "UNSEEN")
    uids = data[0].split() if status == "OK" and data and data[0] else []
    new_uids = filter_new_uids(uids, state)

    if not new_uids:
        send_telegram("📬 Новых писем нет.")
        mail.logout()
        return

    new_uids = new_uids[-MAX_EMAILS:]
    emails_data = collect_emails(mail, new_uids)
    mail.logout()

    if not emails_data:
        send_telegram("📬 Новых писем нет.")
        save_state(update_state_after_run(state, new_uids))
        return

    used_fallback = False
    try:
        if not ANTHROPIC_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        summary = summarize_emails(emails_data)
    except Exception:
        summary = build_fallback_summary(emails_data)
        used_fallback = True

    send_telegram(format_digest(GMAIL_USER, emails_data, summary, used_fallback=used_fallback))
    save_state(update_state_after_run(state, [item["uid"] for item in emails_data]))


if __name__ == "__main__":
    main()
