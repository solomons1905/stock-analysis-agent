"""
Stock Analysis Agent - Main Application
Daily stock market analyzer for Israeli (TASE) and US (NYSE/NASDAQ) markets
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from dotenv import load_dotenv
import yaml

from src.data_fetcher import DataFetcher
from src.technical_analyzer import TechnicalAnalyzer
from src.fundamental_analyzer import FundamentalAnalyzer
from src.scorer import StockScorer
from src.recommender import StockRecommender

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_agent.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class StockAnalysisAgent:
    """Main agent that coordinates all analysis components"""

    def __init__(self, config_path: str = 'config.yml'):
        """
        Initialize the Stock Analysis Agent

        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)

        # Initialize components
        self.fetcher = DataFetcher()
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.scorer = StockScorer(
            weights=self.config.get('scoring', {})
        )
        self.recommender = StockRecommender(
            stop_loss_percent=self.config.get('risk', {}).get('default_stop_loss_percent', 3.0),
            take_profit_percent=self.config.get('risk', {}).get('default_take_profit_percent', 15.0)
        )

        self.logger.info("Stock Analysis Agent initialized")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.logger.info(f"Configuration loaded from {config_path}")
                return config
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return {}
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            return {}

    def analyze_stock(self, symbol: str, market: str = 'us') -> Optional[Dict]:
        """
        Perform complete analysis on a single stock

        Args:
            symbol: Stock symbol
            market: Market type ('us' or 'israel')

        Returns:
            Dictionary with complete analysis and recommendation
        """
        try:
            self.logger.info(f"Analyzing {symbol}...")

            # 1. Fetch data
            self.logger.debug(f"Fetching data for {symbol}")
            historical_data = self.fetcher.fetch_stock_data(symbol, period='1y')
            current_info = self.fetcher.fetch_current_price(symbol)
            fundamental_data = self.fetcher.fetch_fundamental_data(symbol)

            if not current_info or not historical_data is not None:
                self.logger.warning(f"Unable to fetch data for {symbol}")
                return None

            current_price = current_info.get('current_price')
            if not current_price:
                self.logger.warning(f"No price data for {symbol}")
                return None

            # 2. Technical analysis
            self.logger.debug(f"Performing technical analysis for {symbol}")
            technical_data = self.technical_analyzer.analyze(historical_data, symbol)

            # 3. Fundamental analysis
            self.logger.debug(f"Performing fundamental analysis for {symbol}")
            fundamental_analysis = self.fundamental_analyzer.analyze(fundamental_data or {})

            # 4. Scoring
            self.logger.debug(f"Calculating score for {symbol}")
            scores = self.scorer.score(technical_data, fundamental_analysis)

            # 5. Generate recommendation
            self.logger.debug(f"Generating recommendation for {symbol}")
            recommendation = self.recommender.generate_recommendation(
                symbol,
                current_price,
                scores['overall_score'],
                technical_data,
                fundamental_analysis
            )

            # Combine all results
            result = {
                'symbol': symbol,
                'current_price': current_price,
                'market': market,
                'timestamp': datetime.now().isoformat(),
                'technical': technical_data,
                'fundamental': fundamental_analysis,
                'scores': scores,
                'recommendation': recommendation,
            }

            self.logger.info(f"Analysis complete for {symbol}: {recommendation['action']}")
            return result

        except Exception as e:
            self.logger.error(f"Error analyzing {symbol}: {str(e)}")
            return None

    def analyze_universe(self, market: str = 'us') -> List[Dict]:
        """
        Analyze all stocks in a market

        Args:
            market: Market type ('us' or 'israel')

        Returns:
            List of analysis results sorted by recommendation score
        """
        self.logger.info(f"Starting analysis of {market.upper()} market")

        # Get stock symbols
        symbols = self.fetcher.get_stock_universe(market)
        self.logger.info(f"Analyzing {len(symbols)} stocks in {market.upper()}")

        results = []

        for i, symbol in enumerate(symbols, 1):
            self.logger.info(f"[{i}/{len(symbols)}] Analyzing {symbol}")
            result = self.analyze_stock(symbol, market)

            if result:
                results.append(result)

            # Add small delay to avoid rate limiting
            import time
            time.sleep(0.1)

        # Sort by overall score (highest first)
        results.sort(
            key=lambda x: x['scores']['overall_score'],
            reverse=True
        )

        self.logger.info(f"Analysis complete for {market.upper()}: {len(results)} stocks analyzed")
        return results

    def generate_report(self, results: List[Dict], report_path: str = 'reports/') -> str:
        """
        Generate daily report with recommendations

        Args:
            results: List of analysis results
            report_path: Directory to save report

        Returns:
            Path to generated report
        """
        os.makedirs(report_path, exist_ok=True)

        # Generate filename with date
        today = datetime.now().strftime('%Y-%m-%d')
        filename = f"{report_path}stock_recommendations_{today}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Header
                f.write("=" * 80 + "\n")
                f.write(f"DAILY STOCK MARKET ANALYSIS REPORT\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")

                # Summary
                if results:
                    strong_buy = sum(1 for r in results if r['recommendation']['action'] == 'STRONG BUY')
                    buy = sum(1 for r in results if r['recommendation']['action'] == 'BUY')
                    hold = sum(1 for r in results if r['recommendation']['action'] == 'HOLD')
                    sell = sum(1 for r in results if r['recommendation']['action'] == 'SELL')
                    strong_sell = sum(1 for r in results if r['recommendation']['action'] == 'STRONG SELL')

                    f.write("SUMMARY\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Total Stocks Analyzed: {len(results)}\n")
                    f.write(f"STRONG BUY: {strong_buy} | BUY: {buy} | HOLD: {hold} | SELL: {sell} | STRONG SELL: {strong_sell}\n")
                    f.write("\n\n")

                    # Top recommendations (score >= 65)
                    top_recommendations = [r for r in results if r['recommendation']['confidence'] >= 0.65]

                    if top_recommendations:
                        f.write("TOP RECOMMENDATIONS (Confidence >= 65%)\n")
                        f.write("=" * 80 + "\n\n")

                        for result in top_recommendations:
                            f.write(self.recommender.format_recommendation(result['recommendation']))
                            f.write("\n")

                    # All recommendations
                    f.write("\n\nALL RECOMMENDATIONS (sorted by score)\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"{'Symbol':<10} {'Action':<12} {'Score':<8} {'Price':<10} {'Target':<10} {'Risk/Reward':<12}\n")
                    f.write("-" * 80 + "\n")

                    for result in results:
                        symbol = result['symbol']
                        action = result['recommendation']['action']
                        score = result['scores']['overall_score']
                        price = result['current_price']
                        target = result['recommendation']['target_price'] or 'N/A'
                        ratio = result['recommendation']['risk_reward_ratio']

                        target_str = f"${target:.2f}" if target != 'N/A' else target
                        ratio_str = f"{ratio:.2f}:1" if ratio > 0 else "N/A"

                        f.write(f"{symbol:<10} {action:<12} {score:<8} ${price:<9.2f} {target_str:<10} {ratio_str:<12}\n")

                    f.write("\n" + "=" * 80 + "\n")
                    f.write("Report Generated by Stock Analysis Agent\n")
                    f.write("=" * 80 + "\n")
                else:
                    f.write("No analysis results available\n")

            self.logger.info(f"Report saved to {filename}")
            return filename

        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            return ""

    def run_daily_analysis(self):
        """Run complete daily analysis for both markets"""
        try:
            self.logger.info("Starting daily analysis")

            all_results = []

            # Analyze US market
            if self.config.get('markets', {}).get('usa', {}).get('enabled', True):
                us_results = self.analyze_universe('us')
                all_results.extend(us_results)

            # Analyze Israeli market
            if self.config.get('markets', {}).get('israel', {}).get('enabled', True):
                israel_results = self.analyze_universe('israel')
                all_results.extend(israel_results)

            # Generate report
            report_path = self.generate_report(all_results)

            # Send notifications (if configured)
            self._send_notifications(all_results, report_path)

            self.logger.info("Daily analysis complete")
            return all_results

        except Exception as e:
            self.logger.error(f"Error in daily analysis: {str(e)}")
            return []

    def _send_notifications(self, results: List[Dict], report_path: str):
        """
        Send notifications to configured channels
        (Telegram integration will be added here)

        Args:
            results: Analysis results
            report_path: Path to generated report
        """
        # TODO: Implement Telegram notification
        self.logger.info(f"Notifications would be sent here (report: {report_path})")


def main():
    """Main entry point"""
    try:
        # Create agent
        agent = StockAnalysisAgent()

        # Run daily analysis
        results = agent.run_daily_analysis()

        # Print summary
        if results:
            print(f"\n✓ Analysis complete: {len(results)} stocks analyzed")
            print(f"✓ Report generated and saved")
        else:
            print("\n✗ No results generated")

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        exit(1)


if __name__ == '__main__':
    main() 
