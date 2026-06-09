# Gmail Checker

![Preview](assets/preview.svg)

A lightweight utility that watches a Gmail inbox, summarizes unread messages, and delivers the digest to Telegram.

## Why this is stronger now

The useful part of this repo is the workflow: unread Gmail → short digest → Telegram.

The weak part was reliability. A thin demo can look fine until it re-summarizes the same unread emails, fails hard when the AI provider is unavailable, or gives you no deterministic fallback.

This version is more credible because it now:

- tracks processed UIDs instead of trusting `UNSEEN` alone
- reduces duplicate digests across repeated runs
- falls back to a deterministic non-AI digest when Anthropic is unavailable
- splits core logic into testable pieces
- adds tests around state handling, fallback behavior, and parsing

## Good fit for

- daily inbox digests
- monitoring a secondary mailbox
- Telegram-first personal assistant workflows
- scheduled checks via cron or OpenClaw

## Quick start

```bash
git clone https://github.com/Chnurok/gmail-checker.git
cd gmail-checker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 run.py
```

## Configuration

`.env.example`:

```bash
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ANTHROPIC_API_KEY=your_anthropic_key
STATE_FILE=./state.json
MAX_EMAILS=20
SUMMARY_MODEL=claude-haiku-4-5
MAX_BODY_CHARS=1000
MAX_ATTACHMENT_CHARS=500
```

## Behavior notes

- if Anthropic works, you get a compact AI summary
- if Anthropic fails or is not configured, you still get a deterministic fallback digest
- processed UIDs are remembered in `state.json` to reduce duplicate notifications

## Example output

```text
📧 Почта your@gmail.com
4 новых письма

- срочное: письмо от клиента по срокам
- важно: подтверждение оплаты
- не срочно: рассылка сервиса
- спам: рекламное предложение
```

## Run tests

```bash
make test
```

## Security notes

- do **not** commit real credentials
- use environment variables or a secret file outside version control
- Gmail App Passwords should be treated like full mailbox credentials

## Release notes

See `CHANGELOG.md`.

## License

MIT
