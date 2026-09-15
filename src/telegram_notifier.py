"""
Telegram Notification Module
Sends the daily report to Telegram using the plain HTTP Bot API.

The HTTP API is used directly (instead of python-telegram-bot) so there is no
asyncio event-loop juggling and one less dependency to break in CI.
"""

import html
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"
MAX_MESSAGE_LENGTH = 4096
REQUEST_TIMEOUT = 30


class TelegramNotifier:
    """Sends messages and files to a Telegram chat."""

    def __init__(self, bot_token: Optional[str] = None,
                 chat_id: Optional[str] = None):
        self.bot_token = (bot_token or os.getenv('TELEGRAM_BOT_TOKEN') or '').strip()
        self.chat_id = (chat_id or os.getenv('TELEGRAM_CHAT_ID') or '').strip()
        self.logger = logging.getLogger(__name__)

        if not self.bot_token or not self.chat_id:
            self.logger.warning(
                "Telegram is not configured "
                "(TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing)")

    def is_configured(self) -> bool:
        """True when both the token and the chat id are present."""
        return bool(self.bot_token and self.chat_id)

    # ------------------------------------------------------------------ #
    # Low-level transport
    # ------------------------------------------------------------------ #

    def _url(self, method: str) -> str:
        return API_BASE.format(token=self.bot_token, method=method)

    def verify_credentials(self) -> bool:
        """
        Check the token with getMe and log the bot's name.

        Called before sending so a bad token produces a clear message in the
        workflow log rather than a silent failure.
        """
        if not self.is_configured():
            return False

        try:
            response = requests.get(self._url('getMe'), timeout=REQUEST_TIMEOUT)
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Could not reach the Telegram API: %s", exc)
            return False

        if not payload.get('ok'):
            self.logger.error(
                "Telegram rejected the bot token: %s",
                payload.get('description', 'unknown error'))
            return False

        self.logger.info("Telegram bot authenticated as @%s",
                         payload.get('result', {}).get('username', '?'))
        return True

    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a text message, splitting it when it exceeds Telegram's limit.

        Returns True only when every chunk was delivered.
        """
        if not self.is_configured():
            self.logger.warning("Telegram not configured - skipping message")
            return False

        chunks = self._split_message(message)
        all_sent = True

        for index, chunk in enumerate(chunks, 1):
            payload = {
                'chat_id': self.chat_id,
                'text': chunk,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True,
            }

            try:
                response = requests.post(self._url('sendMessage'), data=payload,
                                         timeout=REQUEST_TIMEOUT)
                body = response.json()
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Failed to send message part %d: %s", index, exc)
                all_sent = False
                continue

            if body.get('ok'):
                self.logger.info("Telegram message part %d/%d sent",
                                 index, len(chunks))
            else:
                self.logger.error(
                    "Telegram refused message part %d: %s",
                    index, body.get('description', 'unknown error'))
                all_sent = False

        return all_sent

    # Kept so older call sites keep working.
    send_message_sync = send_message

    def send_document(self, document_path: str, caption: str = '') -> bool:
        """Upload a file to the chat."""
        if not self.is_configured():
            return False

        if not os.path.exists(document_path):
            self.logger.error("Report file not found: %s", document_path)
            return False

        try:
            with open(document_path, 'rb') as handle:
                response = requests.post(
                    self._url('sendDocument'),
                    data={'chat_id': self.chat_id, 'caption': caption[:1024]},
                    files={'document': handle},
                    timeout=120,
                )
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Failed to upload the report: %s", exc)
            return False

        if body.get('ok'):
            self.logger.info("Report uploaded to Telegram")
            return True

        self.logger.error("Telegram refused the report: %s",
                          body.get('description', 'unknown error'))
        return False

    send_document_sync = send_document

    # ------------------------------------------------------------------ #
    # Message building
    # ------------------------------------------------------------------ #

    @staticmethod
    def _split_message(message: str) -> List[str]:
        """Split a long message on line boundaries to respect the 4096 cap."""
        if len(message) <= MAX_MESSAGE_LENGTH:
            return [message]

        chunks, current = [], ""
        for line in message.split("\n"):
            # A single oversized line is hard-cut rather than dropped.
            while len(line) > MAX_MESSAGE_LENGTH:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(line[:MAX_MESSAGE_LENGTH])
                line = line[MAX_MESSAGE_LENGTH:]

            if len(current) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                chunks.append(current)
                current = line
            else:
                current = f"{current}\n{line}" if current else line

        if current:
            chunks.append(current)

        return chunks

    @staticmethod
    def format_recommendations_message(results: List[Dict]) -> str:
        """Build the HTML summary message from the analysis results."""
        if not results:
            return ("<b>Daily Stock Analysis</b>\n"
                    "No results were produced today - check the workflow log.")

        def action_of(result: Dict) -> str:
            return (result.get('recommendation') or {}).get('action', '')

        counts = {label: sum(1 for r in results if action_of(r) == label)
                  for label in ('STRONG BUY', 'BUY', 'HOLD', 'SELL', 'STRONG SELL')}

        lines = [
            "<b>Daily Stock Analysis Report</b>",
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>",
            "",
            "<b>Market summary</b>",
            f"STRONG BUY: {counts['STRONG BUY']}",
            f"BUY: {counts['BUY']}",
            f"HOLD: {counts['HOLD']}",
            f"SELL: {counts['SELL']}",
            f"STRONG SELL: {counts['STRONG SELL']}",
            f"Total analyzed: {len(results)}",
        ]

        top = [r for r in results if action_of(r) in ('STRONG BUY', 'BUY')][:8]

        if top:
            lines += ["", "<b>Top opportunities</b>"]
            for result in top:
                rec = result['recommendation']
                name = html.escape(str(result.get('symbol', '?')))
                currency = rec.get('currency') or ''
                price = rec.get('entry_price')
                target = rec.get('target_price')
                stop = rec.get('stop_loss')

                lines.append(f"\n<b>{name}</b> - {rec['action']} "
                             f"({result['scores']['overall_score']:.0f}/100)")
                if price is not None:
                    lines.append(f"  Entry: {price:.2f} {currency}".rstrip())
                if stop is not None:
                    lines.append(f"  Stop: {stop:.2f}")
                if target is not None:
                    lines.append(f"  Target: {target:.2f}")
        else:
            lines += ["", "<i>No buy signals today.</i>"]

        lines += ["", "<b>Highest scoring</b>", "<code>"]
        lines.append(f"{'Symbol':<10}{'Action':<13}{'Score':>5}")
        lines.append("-" * 28)
        for result in results[:25]:
            rec = result.get('recommendation') or {}
            symbol = str(result.get('symbol', '?'))[:9]
            action = str(rec.get('action', '?'))[:12]
            score = result.get('scores', {}).get('overall_score', 0)
            lines.append(f"{symbol:<10}{action:<13}{score:>5.0f}")
        lines.append("</code>")

        if len(results) > 25:
            lines.append(f"<i>...and {len(results) - 25} more in the attached report</i>")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #

    def send_daily_report(self, results: List[Dict],
                          report_path: Optional[str] = None) -> bool:
        """Send the summary message and attach the full report file."""
        if not self.is_configured():
            return False

        if not self.verify_credentials():
            return False

        sent = self.send_message(self.format_recommendations_message(results))

        if report_path and os.path.exists(report_path):
            self.send_document(report_path, caption='Full analysis report')

        return sent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    notifier = TelegramNotifier()
    if notifier.is_configured() and notifier.verify_credentials():
        notifier.send_message("<b>Test</b>\nStock Analysis Agent is connected.")
    else:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID first.")
