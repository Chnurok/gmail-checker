# Gmail Checker

A small utility that watches a Gmail inbox, summarizes unread messages with Claude, and sends the digest to Telegram.

Built for people who want a lightweight inbox monitor without a full mail client or a heavyweight automation stack.

## What it does

1. logs into Gmail over IMAP
2. finds unread emails
3. extracts sender, subject, and a short text snippet
4. asks Claude for a compact Russian summary
5. delivers the result to Telegram

## Features

- Gmail over IMAP
- compact digest format for unread mail
- Russian summaries out of the box
- simple environment-variable setup
- works well from cron, systemd, or another automation runner

## Project files

- `run.py` — main runnable script
- `checker.py` — alternate entry point
- `.env.example` — config example
- `state.json` — local state file

## Requirements

- Python 3.10+
- Gmail account with 2FA enabled
- Gmail App Password
- Anthropic API key
- Telegram bot token

## Install

```bash
git clone https://github.com/Chnurok/gmail-checker.git
cd gmail-checker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` or export variables directly:

```bash
export GMAIL_USER=your@gmail.com
export GMAIL_APP_PASSWORD=your_gmail_app_password
export TELEGRAM_BOT_TOKEN=your_bot_token
export TELEGRAM_CHAT_ID=your_chat_id
export ANTHROPIC_API_KEY=your_anthropic_key
export STATE_FILE=./state.json
```

## Gmail App Password

1. Enable 2FA in your Google account
2. Open **Security → App passwords**
3. Create a password for Mail
4. Use that value as `GMAIL_APP_PASSWORD`

## Run

```bash
python3 run.py
```

## Example output

```text
📧 Почта your@gmail.com
4 новых письма

- срочное: письмо от клиента по срокам
- важно: подтверждение оплаты
- не срочно: рассылка сервиса
- спам: рекламное предложение
```

## Good fit for

- personal assistant workflows
- secondary mailbox monitoring
- daily or hourly inbox digests
- Telegram-first notification setups

## Security notes

- Do not commit real credentials.
- Use environment variables or a secret file outside the repo.
- Gmail App Passwords should be treated like full-access mailbox credentials.

## License

MIT
