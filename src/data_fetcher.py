"""
Data Fetcher Module
Collects stock price data, volume, and fundamental information from various sources
"""

import yfinance as yf
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class DataFetcher:
    """Fetches stock market data from yfinance and other APIs"""

    # Popular US stocks to analyze (S&P 500 selection)
    US_STOCKS = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX',
        'ADBE', 'CRM', 'INTC', 'AMD', 'AVGO', 'QCOM', 'PYPL', 'SQ',
        'UBER', 'ABNB', 'SHOP', 'ROKU', 'PINS', 'ZM', 'DOCU', 'SNOW',
        'DDOG', 'CRWD', 'NET', 'OKTA', 'TWLO', 'PLAN',
        'JPM', 'BAC', 'WFC', 'GS', 'MS', 'BLK', 'BK', 'PNC',
        'JNJ', 'PFE', 'ABBV', 'MRK', 'LLY', 'AZN', 'TMO', 'ABT',
        'XOM', 'CVX', 'COP', 'MPC', 'PSX', 'VLO', 'OKE', 'MMP',
        'JCI', 'NOW', 'SAP', 'CDNS', 'SNPS', 'MU', 'LRCX', 'KLAC',
        'BA', 'RTX', 'GE', 'HON', 'LMT', 'NOC', 'AXON', 'TXT'
    ]

    # Israeli stocks (TASE)
    ISRAELI_STOCKS = [
        'TASE:AAPL.TA',  # Bank Hapoalim
        'TASE:ALCO.TA',  # Alrov Group
        'TASE:AMRX.TA',  # Compugen
        'TASE:AZRG.TA',  # Azrieli Group
        'TASE:BBIL.TA',  # Bank Leumi
        'TASE:BEZQ.TA',  # Bezeq Group
        'TASE:BLRX.TA',  # BioLineRx
        'TASE:CANN.TA',  # Canopy Growth
        'TASE:DGMI.TA',  # Elad Gold Mines
        'TASE:DSCT.TA',  # Discount Investment
    ]

    def __init__(self):
        """Initialize the Data Fetcher"""
        self.logger = logging.getLogger(__name__)

    def fetch_stock_data(self, symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
        """
        Fetch historical stock data using yfinance

        Args:
            symbol: Stock symbol (e.g., 'AAPL' or 'TASE:AAPL.TA')
            period: Time period ('1y', '6mo', '3mo', '1mo')

        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            self.logger.info(f"Fetching data for {symbol}")
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)

            if df.empty:
                self.logger.warning(f"No data found for {symbol}")
                return None

            # Clean column names
            df.columns = df.columns.str.lower()
            return df

        except Exception as e:
            self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def fetch_current_price(self, symbol: str) -> Optional[Dict]:
        """
        Fetch current price and info for a stock

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with current price data or None if error
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.info

            return {
                'symbol': symbol,
                'current_price': data.get('currentPrice', data.get('regularMarketPrice')),
                'volume': data.get('volume'),
                'market_cap': data.get('marketCap'),
                'pe_ratio': data.get('trailingPE'),
                'dividend_yield': data.get('dividendYield'),
                'fifty_two_week_high': data.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': data.get('fiftyTwoWeekLow'),
                'avg_volume': data.get('averageVolume'),
            }

        except Exception as e:
            self.logger.error(f"Error fetching current price for {symbol}: {str(e)}")
            return None

    def fetch_fundamental_data(self, symbol: str) -> Optional[Dict]:
        """
        Fetch fundamental data for a stock

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with fundamental metrics
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                'symbol': symbol,
                'pe_ratio': info.get('trailingPE'),
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

        except Exception as e:
            self.logger.error(f"Error fetching fundamental data for {symbol}: {str(e)}")
            return None

    def get_stock_universe(self, market: str = "us") -> List[str]:
        """
        Get list of stocks to analyze for a given market

        Args:
            market: 'us' or 'israel'

        Returns:
            List of stock symbols
        """
        if market.lower() == 'us':
            return self.US_STOCKS
        elif market.lower() == 'israel':
            return self.ISRAELI_STOCKS
        else:
            self.logger.warning(f"Unknown market: {market}")
            return []

    def batch_fetch_prices(self, symbols: List[str]) -> pd.DataFrame:
        """
        Fetch prices for multiple stocks efficiently

        Args:
            symbols: List of stock symbols

        Returns:
            DataFrame with current prices for all symbols
        """
        try:
            # Download all at once for efficiency
            data = yf.download(symbols, period="1d", progress=False)

            if len(symbols) == 1:
                # Single symbol returns Series, convert to DataFrame
                current_price = data['Close'].iloc[-1] if len(data) > 0 else None
                return pd.DataFrame({
                    'symbol': [symbols[0]],
                    'price': [current_price]
                })
            else:
                # Multiple symbols return DataFrame
                prices = data['Close'].iloc[-1]
                return pd.DataFrame({
                    'symbol': prices.index,
                    'price': prices.values
                })

        except Exception as e:
            self.logger.error(f"Error in batch fetch: {str(e)}")
            return pd.DataFrame()


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    fetcher = DataFetcher()

    # Test fetching US stock
    print("Testing US stock data fetch...")
    aapl_data = fetcher.fetch_stock_data('AAPL', period='3mo')
    print(f"AAPL data shape: {aapl_data.shape if aapl_data is not None else 'None'}")

    # Test current price
    print("\nTesting current price fetch...")
    current = fetcher.fetch_current_price('AAPL')
    print(f"AAPL current: {current}")

    # Test fundamental data
    print("\nTesting fundamental data fetch...")
    fundamental = fetcher.fetch_fundamental_data('AAPL')
    print(f"AAPL fundamental: {fundamental}") 
