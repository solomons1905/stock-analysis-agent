"""
Telegram Notification Module
Sends daily stock analysis reports and recommendations via Telegram
"""

import logging
import os
from typing import List, Dict, Optional
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications to Telegram"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token (or use TELEGRAM_BOT_TOKEN env var)
            chat_id: Telegram chat ID (or use TELEGRAM_CHAT_ID env var)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.logger = logging.getLogger(__name__)

        if not self.bot_token or not self.chat_id:
            self.logger.warning("Telegram credentials not configured")
            self.bot = None
        else:
            self.bot = Bot(token=self.bot_token)

    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return self.bot is not None

    async def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Send a text message to Telegram

        Args:
            message: Message text (supports HTML formatting)
            parse_mode: 'HTML' or 'Markdown'

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            self.logger.warning("Telegram not configured, skipping notification")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            self.logger.info("Telegram message sent successfully")
            return True
        except TelegramError as e:
            self.logger.error(f"Telegram error: {str(e)}")
            return False

    def send_message_sync(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Synchronous wrapper for send_message

        Args:
            message: Message text
            parse_mode: 'HTML' or 'Markdown'

        Returns:
            True if sent successfully
        """
        try:
            # For Python 3.10+, we can use asyncio.run() directly
            return asyncio.run(self.send_message(message, parse_mode))
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {str(e)}")
            return False

    async def send_document(self, document_path: str, caption: str = '') -> bool:
        """
        Send a document/file to Telegram

        Args:
            document_path: Path to file
            caption: Optional caption

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            self.logger.warning("Telegram not configured, skipping file upload")
            return False

        if not os.path.exists(document_path):
            self.logger.error(f"Document not found: {document_path}")
            return False

        try:
            with open(document_path, 'rb') as f:
                await self.bot.send_document(
                    chat_id=self.chat_id,
                    document=f,
                    caption=caption
                )
            self.logger.info(f"Document sent to Telegram: {document_path}")
            return True
        except TelegramError as e:
            self.logger.error(f"Telegram error sending document: {str(e)}")
            return False

    def send_document_sync(self, document_path: str, caption: str = '') -> bool:
        """Synchronous wrapper for send_document"""
        try:
            return asyncio.run(self.send_document(document_path, caption))
        except Exception as e:
            self.logger.error(f"Error sending Telegram document: {str(e)}")
            return False

    @staticmethod
    def format_recommendations_message(results: List[Dict]) -> str:
        """
        Format analysis results as Telegram message

        Args:
            results: List of analysis results

        Returns:
            Formatted HTML message
        """
        from datetime import datetime

        if not results:
            return "<b>📊 Stock Analysis Report</b>\nNo analysis results available"

        # Count recommendations
        strong_buy = sum(1 for r in results if r['recommendation']['action'] == 'STRONG BUY')
        buy = sum(1 for r in results if r['recommendation']['action'] == 'BUY')
        hold = sum(1 for r in results if r['recommendation']['action'] == 'HOLD')
        sell = sum(1 for r in results if r['recommendation']['action'] == 'SELL')
        strong_sell = sum(1 for r in results if r['recommendation']['action'] == 'STRONG SELL')

        # Header
        message = "<b>📊 Daily Stock Analysis Report</b>\n"
        message += f"<i>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S Israel Time')}</i>\n\n"

        # Summary
        message += "<b>📈 Market Summary</b>\n"
        message += f"🟢 <b>STRONG BUY:</b> {strong_buy}\n"
        message += f"🔵 <b>BUY:</b> {buy}\n"
        message += f"⚪ <b>HOLD:</b> {hold}\n"
        message += f"🟠 <b>SELL:</b> {sell}\n"
        message += f"🔴 <b>STRONG SELL:</b> {strong_sell}\n"
        message += f"<b>Total Analyzed:</b> {len(results)}\n\n"

        # Top recommendations
        top_recommendations = [
            r for r in results
            if r['recommendation']['confidence'] >= 0.75 and r['recommendation']['action'] in ['STRONG BUY', 'BUY']
        ]

        if top_recommendations:
            message += "<b>🌟 Top Recommendations (Confidence ≥ 75%)</b>\n"
            for result in top_recommendations[:5]:  # Limit to top 5
                symbol = result['symbol']
                action = result['recommendation']['action']
                score = result['scores']['overall_score']
                price = result['current_price']
                target = result['recommendation']['target_price']

                message += f"\n<b>{symbol}</b> - {action}\n"
                message += f"  Score: {score}/100\n"
                message += f"  Price: ${price:.2f}\n"
                message += f"  Target: ${target:.2f}\n"

        # All stocks table
        message += "\n<b>📋 All Recommendations</b>\n"
        message += "<code>"
        message += f"{'Symbol':<8} {'Action':<12} {'Score':<6}\n"
        message += "-" * 30 + "\n"

        for result in results[:20]:  # Show top 20
            symbol = result['symbol'][:7]
            action = result['recommendation']['action'][:12]
            score = f"{result['scores']['overall_score']:.0f}"
            message += f"{symbol:<8} {action:<12} {score:<6}\n"

        message += "</code>\n"

        if len(results) > 20:
            message += f"\n<i>...and {len(results) - 20} more stocks</i>"

        message += "\n\n<i>Check the full report for details</i>"

        return message

    def send_daily_report(self, results: List[Dict], report_path: Optional[str] = None) -> bool:
        """
        Send daily analysis report to Telegram

        Args:
            results: List of analysis results
            report_path: Optional path to report file to attach

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            self.logger.warning("Telegram not configured")
            return False

        try:
            # Send message with summary
            message = self.format_recommendations_message(results)
            self.send_message_sync(message, parse_mode='HTML')

            # Send report file if provided
            if report_path and os.path.exists(report_path):
                self.send_document_sync(report_path, caption='📄 Full Analysis Report')

            return True

        except Exception as e:
            self.logger.error(f"Error sending daily report: {str(e)}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    notifier = TelegramNotifier()

    if notifier.is_configured():
        # Example message
        message = """
        <b>Test Message</b>
        This is a test from Stock Analysis Agent
        """
        notifier.send_message_sync(message, parse_mode='HTML')
    else:
        print("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables") 
