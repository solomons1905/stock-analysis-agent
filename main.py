"""
Stock Analysis Agent - main entry point.

Analyses the Israeli (TASE) and US (NYSE / NASDAQ) markets, scores every stock
on technical and fundamental grounds, writes a text report and sends the
summary to Telegram.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

import yaml
from dotenv import load_dotenv

from src.data_fetcher import DataFetcher
from src.fundamental_analyzer import FundamentalAnalyzer
from src.recommender import StockRecommender
from src.scorer import StockScorer
from src.technical_analyzer import TechnicalAnalyzer
from src.telegram_notifier import TelegramNotifier

load_dotenv()

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    handlers=[
        logging.FileHandler('stock_agent.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ],
)

# yfinance is chatty about symbols it cannot resolve; keep the log readable.
logging.getLogger('yfinance').setLevel(logging.ERROR)

logger = logging.getLogger(__name__)


class StockAnalysisAgent:
    """Coordinates fetching, analysis, scoring and reporting."""

    def __init__(self, config_path: str = 'config.yml'):
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)

        self.fetcher = DataFetcher()
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.scorer = StockScorer(weights=self.config.get('scoring'))

        risk = self.config.get('risk') or {}
        self.recommender = StockRecommender(
            stop_loss_percent=risk.get('default_stop_loss_percent', 3.0),
            take_profit_percent=risk.get('default_take_profit_percent', 15.0),
        )

        self.logger.info("Stock Analysis Agent ready")

    # ------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------ #

    def _load_config(self, config_path: str) -> Dict:
        """Load config.yml, falling back to defaults when it is missing."""
        try:
            with open(config_path, 'r', encoding='utf-8') as handle:
                config = yaml.safe_load(handle) or {}
            self.logger.info("Loaded configuration from %s", config_path)
            return config
        except FileNotFoundError:
            self.logger.warning("No %s found - using defaults", config_path)
            return {}
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Could not read %s: %s", config_path, exc)
            return {}

    # ------------------------------------------------------------------ #
    # Per-stock analysis
    # ------------------------------------------------------------------ #

    def analyze_stock(self, symbol: str, market: str = 'us') -> Optional[Dict]:
        """Run the full pipeline for one symbol. Returns None when data is missing."""
        try:
            history = self.fetcher.fetch_stock_data(symbol, period='1y')
            if history is None or len(history) < 30:
                self.logger.warning("Skipping %s - not enough price history", symbol)
                return None

            quote = self.fetcher.fetch_current_price(symbol, history)
            if not quote or not quote.get('current_price'):
                self.logger.warning("Skipping %s - no current price", symbol)
                return None

            current_price = quote['current_price']
            fundamentals_raw = self.fetcher.fetch_fundamental_data(symbol)

            technical = self.technical_analyzer.analyze(history, symbol)
            fundamental = self.fundamental_analyzer.analyze(fundamentals_raw)
            scores = self.scorer.score(technical, fundamental)

            recommendation = self.recommender.generate_recommendation(
                symbol,
                current_price,
                scores['overall_score'],
                technical,
                fundamental,
                currency=quote.get('currency') or ('ILS' if market == 'israel' else 'USD'),
            )

            self.logger.info("%-10s %-12s score %.1f",
                             symbol, recommendation['action'],
                             scores['overall_score'])

            return {
                'symbol': symbol,
                'name': quote.get('name', symbol),
                'current_price': current_price,
                'currency': quote.get('currency'),
                'market': market,
                'timestamp': datetime.now().isoformat(timespec='seconds'),
                'technical': technical,
                'fundamental': fundamental,
                'scores': scores,
                'recommendation': recommendation,
            }

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Analysis failed for %s: %s", symbol, exc)
            return None

    def analyze_universe(self, market: str = 'us',
                         limit: Optional[int] = None) -> List[Dict]:
        """Analyse every stock in a market, best score first."""
        symbols = self.fetcher.get_stock_universe(market)
        if limit:
            symbols = symbols[:limit]

        self.logger.info("Analysing %d stocks in %s", len(symbols), market.upper())

        results: List[Dict] = []
        for index, symbol in enumerate(symbols, 1):
            self.logger.debug("[%d/%d] %s", index, len(symbols), symbol)

            result = self.analyze_stock(symbol, market)
            if result:
                results.append(result)

            # Be gentle with the Yahoo endpoints.
            time.sleep(0.3)

        # Free the cached ticker.info payloads before the next market.
        self.fetcher.clear_cache()

        results.sort(key=lambda r: r['scores']['overall_score'], reverse=True)
        self.logger.info("%s complete: %d of %d stocks analysed",
                         market.upper(), len(results), len(symbols))
        return results

    # ------------------------------------------------------------------ #
    # Reporting
    # ------------------------------------------------------------------ #

    def generate_report(self, results: List[Dict],
                        report_dir: str = 'reports') -> str:
        """Write the full text report and return its path."""
        os.makedirs(report_dir, exist_ok=True)

        filename = os.path.join(
            report_dir,
            f"stock_recommendations_{datetime.now().strftime('%Y-%m-%d')}.txt")

        try:
            with open(filename, 'w', encoding='utf-8') as handle:
                handle.write("=" * 70 + "\n")
                handle.write("DAILY STOCK MARKET ANALYSIS REPORT\n")
                handle.write(
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                handle.write("=" * 70 + "\n\n")

                if not results:
                    handle.write("No analysis results were produced.\n")
                    self.logger.warning("Report written with no results")
                    return filename

                counts = {label: sum(
                    1 for r in results
                    if r['recommendation']['action'] == label)
                    for label in ('STRONG BUY', 'BUY', 'HOLD', 'SELL', 'STRONG SELL')}

                handle.write("SUMMARY\n")
                handle.write("-" * 70 + "\n")
                handle.write(f"Total stocks analysed: {len(results)}\n")
                for label, count in counts.items():
                    handle.write(f"  {label:<12} {count}\n")
                handle.write("\n\n")

                buys = [r for r in results
                        if r['recommendation']['action'] in ('STRONG BUY', 'BUY')]

                if buys:
                    handle.write("BUY RECOMMENDATIONS\n")
                    handle.write("=" * 70 + "\n\n")
                    for result in buys:
                        handle.write(self.recommender.format_recommendation(
                            result['recommendation']))
                        handle.write("\n")

                handle.write("\nALL STOCKS (sorted by score)\n")
                handle.write("=" * 70 + "\n")
                handle.write(f"{'Symbol':<10}{'Action':<13}{'Score':>6}"
                             f"{'Price':>12}{'Target':>12}{'R/R':>8}\n")
                handle.write("-" * 70 + "\n")

                for result in results:
                    rec = result['recommendation']
                    target = rec.get('target_price')
                    ratio = rec.get('risk_reward_ratio') or 0

                    handle.write(
                        f"{result['symbol']:<10}"
                        f"{rec['action']:<13}"
                        f"{result['scores']['overall_score']:>6.1f}"
                        f"{result['current_price']:>12.2f}"
                        f"{(f'{target:.2f}' if target else '-'):>12}"
                        f"{(f'{ratio:.2f}' if ratio else '-'):>8}\n")

                handle.write("\n" + "=" * 70 + "\n")
                handle.write("This report is generated automatically for "
                             "informational purposes only.\n")
                handle.write("It is not investment advice. Do your own research.\n")
                handle.write("=" * 70 + "\n")

            self.logger.info("Report written to %s", filename)
            return filename

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Could not write the report: %s", exc)
            return ""

    # ------------------------------------------------------------------ #
    # Orchestration
    # ------------------------------------------------------------------ #

    def run_daily_analysis(self, limit: Optional[int] = None) -> List[Dict]:
        """Analyse every enabled market, write the report and notify."""
        markets = self.config.get('markets') or {}
        all_results: List[Dict] = []

        if (markets.get('usa') or {}).get('enabled', True):
            all_results.extend(self.analyze_universe('us', limit))

        if (markets.get('israel') or {}).get('enabled', True):
            all_results.extend(self.analyze_universe('israel', limit))

        all_results.sort(key=lambda r: r['scores']['overall_score'], reverse=True)

        report_path = self.generate_report(all_results)
        self._send_notifications(all_results, report_path)

        return all_results

    def _send_notifications(self, results: List[Dict], report_path: str) -> None:
        """Send the Telegram notification, if it is configured."""
        try:
            notifier = TelegramNotifier()
            if not notifier.is_configured():
                self.logger.info(
                    "Telegram is not configured - set TELEGRAM_BOT_TOKEN and "
                    "TELEGRAM_CHAT_ID to receive the report")
                return

            if notifier.send_daily_report(results, report_path):
                self.logger.info("Telegram report delivered")
            else:
                self.logger.error("Telegram report was not delivered")

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Notification step failed: %s", exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily stock market analysis")
    parser.add_argument('--limit', type=int, default=None,
                        help="Only analyse the first N stocks per market "
                             "(useful for a quick test run)")
    parser.add_argument('--market', choices=['us', 'israel', 'both'],
                        default='both', help="Which market to analyse")
    args = parser.parse_args()

    try:
        agent = StockAnalysisAgent()

        if args.market == 'both':
            results = agent.run_daily_analysis(limit=args.limit)
        else:
            results = agent.analyze_universe(args.market, limit=args.limit)
            report = agent.generate_report(results)
            agent._send_notifications(results, report)

        if results:
            print(f"\nDone: {len(results)} stocks analysed.")
            return 0

        print("\nNo stocks could be analysed - check stock_agent.log.")
        return 1

    except Exception as exc:  # noqa: BLE001
        logger.exception("Fatal error: %s", exc)
        return 1


if __name__ == '__main__':
    sys.exit(main())
