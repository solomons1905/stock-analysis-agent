"""
Technical Analysis Module
Calculates technical indicators: RSI, MACD, Moving Averages, Bollinger Bands, Volume
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Performs technical analysis on stock price data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ==================== Moving Averages ====================
    @staticmethod
    def calculate_moving_average(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA)

        Args:
            df: DataFrame with 'close' column
            period: Number of periods for MA

        Returns:
            Series with moving average values
        """
        return df['close'].rolling(window=period).mean()

    def get_moving_averages(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """
        Calculate multiple moving averages: 20, 50, 200 day

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with MA20, MA50, MA200 and current trend
        """
        if len(df) < 200:
            self.logger.warning(f"Insufficient data for MA calculation. Need 200+ days, got {len(df)}")
            return {}

        ma20 = self.calculate_moving_average(df, 20).iloc[-1]
        ma50 = self.calculate_moving_average(df, 50).iloc[-1]
        ma200 = self.calculate_moving_average(df, 200).iloc[-1]
        current_price = df['close'].iloc[-1]

        # Determine trend
        if current_price > ma20 > ma50 > ma200:
            trend = "strong_uptrend"
        elif current_price > ma50 > ma200:
            trend = "uptrend"
        elif current_price < ma20 < ma50 < ma200:
            trend = "strong_downtrend"
        elif current_price < ma50 < ma200:
            trend = "downtrend"
        else:
            trend = "neutral"

        return {
            'ma20': round(ma20, 2),
            'ma50': round(ma50, 2),
            'ma200': round(ma200, 2),
            'current_price': round(current_price, 2),
            'trend': trend
        }

    # ==================== RSI (Relative Strength Index) ====================
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Calculate RSI (Relative Strength Index)
        RSI < 30 = oversold (potential buy)
        RSI > 70 = overbought (potential sell)

        Args:
            df: DataFrame with 'close' column
            period: Period for RSI (default 14)

        Returns:
            RSI value or None if insufficient data
        """
        if len(df) < period + 1:
            return None

        close = df['close']

        # Calculate price changes
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # Calculate RS and RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return round(rsi.iloc[-1], 2)

    def get_rsi_signal(self, rsi: float) -> str:
        """
        Get buy/sell signal from RSI value

        Args:
            rsi: RSI value

        Returns:
            Signal: 'strong_buy', 'buy', 'neutral', 'sell', 'strong_sell'
        """
        if rsi < 30:
            return "strong_buy"
        elif rsi < 45:
            return "buy"
        elif rsi < 55:
            return "neutral"
        elif rsi < 70:
            return "sell"
        else:
            return "strong_sell"

    # ==================== MACD (Moving Average Convergence Divergence) ====================
    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Optional[float]]:
        """
        Calculate MACD and Signal line

        Args:
            df: DataFrame with 'close' column
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)

        Returns:
            Dictionary with MACD, Signal, and Histogram
        """
        if len(df) < slow + signal:
            return {}

        close = df['close']

        # Calculate EMAs
        ema_fast = close.ewm(span=fast).mean()
        ema_slow = close.ewm(span=slow).mean()

        # Calculate MACD and Signal
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        histogram = macd - macd_signal

        return {
            'macd': round(macd.iloc[-1], 4),
            'signal': round(macd_signal.iloc[-1], 4),
            'histogram': round(histogram.iloc[-1], 4),
        }

    def get_macd_signal(self, macd_data: Dict) -> str:
        """
        Get buy/sell signal from MACD

        Args:
            macd_data: Dictionary with macd, signal, histogram

        Returns:
            Signal: 'buy', 'sell', or 'neutral'
        """
        if not macd_data:
            return "neutral"

        macd = macd_data.get('macd', 0)
        signal = macd_data.get('signal', 0)
        histogram = macd_data.get('histogram', 0)

        if histogram > 0 and macd > signal:
            return "buy"
        elif histogram < 0 and macd < signal:
            return "sell"
        else:
            return "neutral"

    # ==================== Bollinger Bands ====================
    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, Optional[float]]:
        """
        Calculate Bollinger Bands

        Args:
            df: DataFrame with 'close' column
            period: Period for SMA (default 20)
            std_dev: Standard deviation multiplier (default 2)

        Returns:
            Dictionary with upper band, middle band, lower band
        """
        if len(df) < period:
            return {}

        close = df['close']

        # Calculate SMA and standard deviation
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()

        # Calculate bands
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)

        return {
            'upper': round(upper.iloc[-1], 2),
            'middle': round(sma.iloc[-1], 2),
            'lower': round(lower.iloc[-1], 2),
        }

    def get_bollinger_signal(self, current_price: float, bb_data: Dict) -> str:
        """
        Get buy/sell signal from Bollinger Bands

        Args:
            current_price: Current stock price
            bb_data: Dictionary with upper, middle, lower

        Returns:
            Signal: 'buy', 'sell', or 'neutral'
        """
        if not bb_data:
            return "neutral"

        upper = bb_data.get('upper', 0)
        lower = bb_data.get('lower', 0)
        middle = bb_data.get('middle', 0)

        if current_price < lower:
            return "buy"  # Oversold
        elif current_price > upper:
            return "sell"  # Overbought
        elif current_price < middle:
            return "buy"  # Below middle
        else:
            return "sell"  # Above middle

    # ==================== Volume Analysis ====================
    @staticmethod
    def analyze_volume(df: pd.DataFrame, period: int = 20) -> Dict[str, Optional[float]]:
        """
        Analyze volume trends

        Args:
            df: DataFrame with 'volume' column
            period: Period for average volume

        Returns:
            Dictionary with volume metrics
        """
        if len(df) < period or 'volume' not in df.columns:
            return {}

        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(period).mean()
        volume_trend = current_volume / avg_volume if avg_volume > 0 else 0

        return {
            'current_volume': int(current_volume),
            'avg_volume': round(avg_volume),
            'volume_ratio': round(volume_trend, 2),  # > 1 means above average
        }

    def get_volume_signal(self, volume_data: Dict, price_trend: str) -> str:
        """
        Get signal from volume analysis

        Args:
            volume_data: Dictionary with volume metrics
            price_trend: 'uptrend' or 'downtrend'

        Returns:
            Signal confidence: 'strong', 'weak', or 'neutral'
        """
        if not volume_data:
            return "neutral"

        ratio = volume_data.get('volume_ratio', 1)

        if ratio > 1.5:
            return "strong"  # High volume confirms trend
        elif ratio < 0.7:
            return "weak"  # Low volume, trend may reverse
        else:
            return "neutral"

    # ==================== Full Technical Analysis ====================
    def analyze(self, df: pd.DataFrame, symbol: str = "") -> Dict:
        """
        Perform complete technical analysis on stock data

        Args:
            df: DataFrame with OHLCV data
            symbol: Stock symbol (for logging)

        Returns:
            Dictionary with all technical indicators
        """
        if df is None or len(df) < 50:
            self.logger.warning(f"Insufficient data for technical analysis of {symbol}")
            return {}

        try:
            # Calculate all indicators
            ma_data = self.get_moving_averages(df)
            rsi = self.calculate_rsi(df)
            macd_data = self.calculate_macd(df)
            bb_data = self.calculate_bollinger_bands(df)
            volume_data = self.analyze_volume(df)

            # Get current price for Bollinger Bands signal
            current_price = df['close'].iloc[-1] if 'close' in df.columns else 0

            # Get signals
            rsi_signal = self.get_rsi_signal(rsi) if rsi else "neutral"
            macd_signal = self.get_macd_signal(macd_data)
            bb_signal = self.get_bollinger_signal(current_price, bb_data)
            volume_signal = self.get_volume_signal(volume_data, ma_data.get('trend', ''))

            return {
                'moving_averages': ma_data,
                'rsi': rsi,
                'rsi_signal': rsi_signal,
                'macd': macd_data,
                'macd_signal': macd_signal,
                'bollinger_bands': bb_data,
                'bollinger_signal': bb_signal,
                'volume': volume_data,
                'volume_signal': volume_signal,
            }

        except Exception as e:
            self.logger.error(f"Error in technical analysis for {symbol}: {str(e)}")
            return {}


# Example usage
if __name__ == "__main__":
    import yfinance as yf

    logging.basicConfig(level=logging.INFO)

    analyzer = TechnicalAnalyzer()

    # Fetch sample data
    print("Fetching AAPL data...")
    aapl = yf.Ticker('AAPL')
    df = aapl.history(period='1y')
    df.columns = df.columns.str.lower()

    # Analyze
    print("\nPerforming technical analysis...")
    result = analyzer.analyze(df, 'AAPL')

    print(f"\nMoving Averages: {result['moving_averages']}")
    print(f"RSI: {result['rsi']} (Signal: {result['rsi_signal']})")
    print(f"MACD: {result['macd']} (Signal: {result['macd_signal']})")
    print(f"Bollinger Bands: {result['bollinger_bands']} (Signal: {result['bollinger_signal']})")
    print(f"Volume: {result['volume']} (Signal: {result['volume_signal']})") 
