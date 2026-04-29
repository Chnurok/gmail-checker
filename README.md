# Gmail Checker

A small utility that watches a Gmail inbox, summarizes unread messages with Claude, and delivers the result to Telegram.

## Features

- 📧 Connects to Gmail over IMAP
- 📨 Reads unread messages from the inbox
- ✍️ Builds a compact Russian summary with Claude
- 🤖 Sends the digest to Telegram
- ⚙️ Simple environment-variable configuration
- 🧩 Easy to run manually, from cron, or from another automation layer

## Files

- `run.py` — main runnable version
- `checker.py` — alternative entry point using the same env-based configuration style
- `.env.example` — example configuration
- `state.json` — local state file for tracking checks

## Requirements

- Python 3.10+
- Gmail account with 2FA enabled
- Gmail App Password
- Anthropic API key
- Telegram bot token

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` and fill in the values via your shell, systemd, cron wrapper, or secret manager.

```bash
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
ANTHROPIC_API_KEY=your_anthropic_key
STATE_FILE=./state.json
```

## Gmail App Password

1. Enable 2FA in your Google account
2. Open **Security → App passwords**
3. Create a password for Mail
4. Use that value in `GMAIL_APP_PASSWORD`

## Run

```bash
python3 run.py
```

## What it does

1. Logs into Gmail over IMAP
2. Finds unread messages
3. Extracts sender, subject, and text snippets
4. Asks Claude for a short summary in Russian
5. Sends the summary to Telegram

## Example usage patterns

- daily inbox digest
- lightweight monitoring for a secondary mailbox
- Telegram-first personal assistant workflows
- scheduled checks via cron or OpenClaw-triggered runs

## Security note

Do **not** commit real credentials into the repository. Use environment variables or a secret file outside version control.

## License

MIT
