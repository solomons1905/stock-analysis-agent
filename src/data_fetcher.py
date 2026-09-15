"""
Data Fetcher Module
Collects stock price data, volume, and fundamental information from Yahoo Finance.
"""

import logging
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches stock market data from yfinance."""

    # Large-cap US stocks (NYSE / NASDAQ)
    US_STOCKS = [
        # Mega-cap tech
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX',
        'ADBE', 'CRM', 'ORCL', 'CSCO', 'IBM',
        # Semiconductors
        'AMD', 'INTC', 'AVGO', 'QCOM', 'MU', 'LRCX', 'KLAC', 'AMAT', 'TXN',
        'CDNS', 'SNPS', 'ARM',
        # Software / internet
        'NOW', 'SNOW', 'DDOG', 'CRWD', 'NET', 'OKTA', 'TWLO', 'ZM', 'DOCU',
        'SHOP', 'UBER', 'ABNB', 'PINS', 'ROKU', 'PLTR', 'PANW',
        # Financials
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'PNC', 'AXP', 'V', 'MA',
        'PYPL', 'SCHW',
        # Healthcare
        'JNJ', 'PFE', 'ABBV', 'MRK', 'LLY', 'AZN', 'TMO', 'ABT', 'UNH',
        'AMGN', 'GILD', 'BMY',
        # Energy
        'XOM', 'CVX', 'COP', 'MPC', 'PSX', 'VLO', 'OKE', 'SLB',
        # Industrials / defense
        'BA', 'RTX', 'GE', 'HON', 'LMT', 'NOC', 'CAT', 'DE', 'UPS',
        # Consumer
        'WMT', 'COST', 'HD', 'MCD', 'NKE', 'SBUX', 'PG', 'KO', 'PEP', 'DIS',
    ]

    # Tel Aviv Stock Exchange (TASE). Yahoo Finance uses the ".TA" suffix.
    ISRAELI_STOCKS = [
        # Banks & insurance
        'POLI.TA',   # Bank Hapoalim
        'LUMI.TA',   # Bank Leumi
        'MZTF.TA',   # Mizrahi Tefahot
        'DSCT.TA',   # Israel Discount Bank
        'FIBI.TA',   # First International Bank
        'PHOE.TA',   # Phoenix Holdings
        'HARL.TA',   # Harel Insurance
        'MGDL.TA',   # Migdal Insurance
        'CLIS.TA',   # Clal Insurance
        # Technology
        'NICE.TA',   # NICE
        'ESLT.TA',   # Elbit Systems
        'TSEM.TA',   # Tower Semiconductor
        'CAMT.TA',   # Camtek
        'NVMI.TA',   # Nova
        'SPNS.TA',   # Sapiens
        'MGIC.TA',   # Magic Software
        'ELTR.TA',   # Eltek
        # Pharma & chemicals
        'TEVA.TA',   # Teva Pharmaceutical
        'ICL.TA',    # ICL Group
        # Real estate & infrastructure
        'AZRG.TA',   # Azrieli Group
        'MLSR.TA',   # Melisron
        'BIG.TA',    # Big Shopping Centers
        'AMOT.TA',   # Amot Investments
        'SLARL.TA',  # Shapir Engineering
        # Telecom, energy & retail
        'BEZQ.TA',   # Bezeq
        'CEL.TA',    # Cellcom
        'PTNR.TA',   # Partner Communications
        'ORA.TA',    # Ormat Technologies
        'ENLT.TA',   # Enlight Renewable Energy
        'NVPT.TA',   # NewMed Energy
        'SAE.TA',    # Shufersal
        'RMLI.TA',   # Rami Levy
        'STRS.TA',   # Strauss Group
        'ELCO.TA',   # Elco
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._info_cache: Dict[str, Dict] = {}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _get_info(self, symbol: str) -> Dict:
        """
        Fetch and cache ticker.info for a symbol.

        ticker.info is a slow network call, so it is fetched once per symbol
        and reused by both the price and the fundamental lookups.
        """
        if symbol in self._info_cache:
            return self._info_cache[symbol]

        info: Dict = {}
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception as exc:  # noqa: BLE001 - yfinance raises many types
            self.logger.warning("Could not fetch info for %s: %s", symbol, exc)
            info = {}

        self._info_cache[symbol] = info
        return info

    def clear_cache(self) -> None:
        """Drop the cached ticker.info responses."""
        self._info_cache.clear()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def fetch_stock_data(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Fetch historical OHLCV data.

        Args:
            symbol: Stock symbol, e.g. 'AAPL' or 'POLI.TA'.
            period: Time period accepted by yfinance ('1y', '6mo', '3mo', ...).

        Returns:
            DataFrame with lowercase column names, or None on failure.
        """
        try:
            df = yf.Ticker(symbol).history(period=period, auto_adjust=True)

            if df is None or df.empty:
                self.logger.warning("No price history for %s", symbol)
                return None

            df.columns = [str(c).lower() for c in df.columns]

            if 'close' not in df.columns:
                self.logger.warning("No close column for %s", symbol)
                return None

            return df

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Error fetching history for %s: %s", symbol, exc)
            return None

    def fetch_current_price(self, symbol: str,
                            history: Optional[pd.DataFrame] = None) -> Optional[Dict]:
        """
        Fetch the current price and headline figures for a stock.

        If ``history`` is supplied it is used as a fallback price source when
        ticker.info does not expose a quote, which happens often for TASE
        symbols.
        """
        info = self._get_info(symbol)

        price = (
            info.get('currentPrice')
            or info.get('regularMarketPrice')
            or info.get('previousClose')
        )

        # Fall back to the last close from the history we already downloaded.
        if price is None and history is not None and not history.empty:
            try:
                price = float(history['close'].iloc[-1])
            except (KeyError, IndexError, ValueError):
                price = None

        if price is None:
            self.logger.warning("No price available for %s", symbol)
            return None

        return {
            'symbol': symbol,
            'current_price': float(price),
            'currency': info.get('currency'),
            'name': info.get('shortName') or info.get('longName') or symbol,
            'volume': info.get('volume'),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'dividend_yield': info.get('dividendYield'),
            'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
            'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
            'avg_volume': info.get('averageVolume'),
        }

    def fetch_fundamental_data(self, symbol: str) -> Dict:
        """Fetch fundamental metrics for a stock. Returns {} when unavailable."""
        info = self._get_info(symbol)

        if not info:
            return {'symbol': symbol}

        return {
            'symbol': symbol,
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'roe': info.get('returnOnEquity'),
            'revenue': info.get('totalRevenue'),
            'net_income': info.get('netIncomeToCommon'),
            'debt_to_equity': info.get('debtToEquity'),
            'profit_margin': info.get('profitMargins'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'dividend_yield': info.get('dividendYield'),
            'payout_ratio': info.get('payoutRatio'),
        }

    def get_stock_universe(self, market: str = "us") -> List[str]:
        """Return the list of symbols to analyze for a market ('us' or 'israel')."""
        market = (market or "").lower()

        if market == 'us':
            return list(self.US_STOCKS)
        if market in ('israel', 'il', 'tase'):
            return list(self.ISRAELI_STOCKS)

        self.logger.warning("Unknown market: %s", market)
        return []


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fetcher = DataFetcher()

    hist = fetcher.fetch_stock_data('AAPL', period='6mo')
    print("History rows:", 0 if hist is None else len(hist))

    print("Quote:", fetcher.fetch_current_price('AAPL', hist))
    print("Fundamentals:", fetcher.fetch_fundamental_data('AAPL'))
