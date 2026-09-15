"""
Helper: find your Telegram chat id.

Send any message to your bot in Telegram first, then run this script. It reads
the bot's pending updates and prints the chat id of everyone who wrote to it.

Locally:
    set TELEGRAM_BOT_TOKEN=123456:ABC...   (Windows)
    python get_chat_id.py

On GitHub: run the "Find Telegram Chat ID" workflow and read its log.
"""

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()


def main() -> int:
    token = (os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()

    if not token:
        print("TELEGRAM_BOT_TOKEN is not set.")
        print("Put it in your .env file, or add it as a GitHub secret.")
        return 1

    try:
        who = requests.get(
            f"https://api.telegram.org/bot{token}/getMe", timeout=30).json()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not reach Telegram: {exc}")
        return 1

    if not who.get('ok'):
        print(f"The token was rejected: {who.get('description')}")
        print("Copy it again from @BotFather - it looks like 123456789:AAE...")
        return 1

    username = who['result'].get('username', '?')
    print(f"Bot authenticated: @{username}\n")

    try:
        updates = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates", timeout=30).json()
    except Exception as exc:  # noqa: BLE001
        print(f"Could not read updates: {exc}")
        return 1

    if not updates.get('ok'):
        print(f"Telegram returned an error: {updates.get('description')}")
        return 1

    found = {}
    for update in updates.get('result', []):
        # A message can arrive as a normal message, a channel post or an edit.
        for key in ('message', 'edited_message', 'channel_post',
                    'edited_channel_post'):
            chat = (update.get(key) or {}).get('chat')
            if chat:
                found[chat['id']] = chat

    if not found:
        print("No messages found.\n")
        print("Do this, then run it again:")
        print(f"  1. Open Telegram and search for @{username}")
        print("  2. Open the chat and press Start, or send it any message")
        print("  3. Run this again within a few minutes")
        return 1

    print("Chat ids found - use the one that matches where you want the report:\n")
    for chat_id, chat in found.items():
        title = (chat.get('title')
                 or " ".join(filter(None, [chat.get('first_name'),
                                           chat.get('last_name')]))
                 or chat.get('username')
                 or "(no name)")
        print(f"  TELEGRAM_CHAT_ID = {chat_id}")
        print(f"      type: {chat.get('type')}   name: {title}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
