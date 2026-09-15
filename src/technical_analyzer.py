"""
Technical Analysis Module
Calculates RSI, MACD, Moving Averages, Bollinger Bands and volume metrics.
"""

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    """Performs technical analysis on stock price data."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------ #
    # Moving averages
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_moving_average(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Simple moving average of the close price."""
        return df['close'].rolling(window=period).mean()

    def get_moving_averages(self, df: pd.DataFrame) -> Dict:
        """
        Calculate the 20/50/200 day moving averages and derive a trend label.

        Longer averages are skipped (set to None) when there is not enough
        history, instead of discarding the whole result.
        """
        if df is None or df.empty or 'close' not in df.columns:
            return {}

        def ma(period: int) -> Optional[float]:
            if len(df) < period:
                return None
            value = self.calculate_moving_average(df, period).iloc[-1]
            return None if pd.isna(value) else round(float(value), 2)

        ma20, ma50, ma200 = ma(20), ma(50), ma(200)
        current_price = float(df['close'].iloc[-1])

        # Compare only against the averages we actually have.
        trend = "neutral"
        if ma20 and ma50 and ma200:
            if current_price > ma20 > ma50 > ma200:
                trend = "strong_uptrend"
            elif current_price > ma50 > ma200:
                trend = "uptrend"
            elif current_price < ma20 < ma50 < ma200:
                trend = "strong_downtrend"
            elif current_price < ma50 < ma200:
                trend = "downtrend"
        elif ma20 and ma50:
            if current_price > ma20 > ma50:
                trend = "uptrend"
            elif current_price < ma20 < ma50:
                trend = "downtrend"

        return {
            'ma20': ma20,
            'ma50': ma50,
            'ma200': ma200,
            'current_price': round(current_price, 2),
            'trend': trend,
        }

    # ------------------------------------------------------------------ #
    # RSI
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Relative Strength Index.

        RSI below 30 is considered oversold, above 70 overbought.
        """
        if df is None or len(df) < period + 1 or 'close' not in df.columns:
            return None

        delta = df['close'].diff()
        gain = delta.clip(lower=0).rolling(window=period).mean()
        loss = (-delta.clip(upper=0)).rolling(window=period).mean()

        last_gain = gain.iloc[-1]
        last_loss = loss.iloc[-1]

        if pd.isna(last_gain) or pd.isna(last_loss):
            return None

        # No losses in the window means a maximal RSI; guard the division.
        if last_loss == 0:
            return 100.0 if last_gain > 0 else 50.0

        rs = last_gain / last_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return round(float(rsi), 2)

    @staticmethod
    def get_rsi_signal(rsi: Optional[float]) -> str:
        """Map an RSI value onto a buy/sell signal."""
        if rsi is None:
            return "neutral"
        if rsi < 30:
            return "strong_buy"
        if rsi < 45:
            return "buy"
        if rsi < 55:
            return "neutral"
        if rsi < 70:
            return "sell"
        return "strong_sell"

    # ------------------------------------------------------------------ #
    # MACD
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26,
                       signal: int = 9) -> Dict:
        """MACD line, signal line and histogram."""
        if df is None or len(df) < slow + signal or 'close' not in df.columns:
            return {}

        close = df['close']
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()

        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - macd_signal

        if pd.isna(macd.iloc[-1]) or pd.isna(macd_signal.iloc[-1]):
            return {}

        return {
            'macd': round(float(macd.iloc[-1]), 4),
            'signal': round(float(macd_signal.iloc[-1]), 4),
            'histogram': round(float(histogram.iloc[-1]), 4),
        }

    @staticmethod
    def get_macd_signal(macd_data: Dict) -> str:
        """Buy when the MACD sits above its signal line, sell when below."""
        if not macd_data:
            return "neutral"

        macd = macd_data.get('macd', 0.0)
        signal = macd_data.get('signal', 0.0)
        histogram = macd_data.get('histogram', 0.0)

        if histogram > 0 and macd > signal:
            return "buy"
        if histogram < 0 and macd < signal:
            return "sell"
        return "neutral"

    # ------------------------------------------------------------------ #
    # Bollinger Bands
    # ------------------------------------------------------------------ #

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20,
                                  std_dev: float = 2.0) -> Dict:
        """Upper, middle and lower Bollinger Bands."""
        if df is None or len(df) < period or 'close' not in df.columns:
            return {}

        close = df['close']
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()

        if pd.isna(sma.iloc[-1]) or pd.isna(std.iloc[-1]):
            return {}

        middle = float(sma.iloc[-1])
        spread = float(std.iloc[-1]) * std_dev

        return {
            'upper': round(middle + spread, 2),
            'middle': round(middle, 2),
            'lower': round(middle - spread, 2),
        }

    @staticmethod
    def get_bollinger_signal(current_price: float, bb_data: Dict) -> str:
        """Price below the lower band is oversold, above the upper band overbought."""
        if not bb_data or not current_price:
            return "neutral"

        upper = bb_data.get('upper')
        lower = bb_data.get('lower')
        middle = bb_data.get('middle')

        if lower is not None and current_price < lower:
            return "strong_buy"
        if upper is not None and current_price > upper:
            return "strong_sell"
        if middle is not None and current_price < middle:
            return "buy"
        return "sell"

    # ------------------------------------------------------------------ #
    # Volume
    # ------------------------------------------------------------------ #

    @staticmethod
    def analyze_volume(df: pd.DataFrame, period: int = 20) -> Dict:
        """Compare the latest volume against its recent average."""
        if df is None or len(df) < period or 'volume' not in df.columns:
            return {}

        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(period).mean()

        if pd.isna(current_volume) or pd.isna(avg_volume) or avg_volume <= 0:
            return {}

        return {
            'current_volume': int(current_volume),
            'avg_volume': int(avg_volume),
            'volume_ratio': round(float(current_volume) / float(avg_volume), 2),
        }

    @staticmethod
    def get_volume_signal(volume_data: Dict) -> str:
        """High relative volume confirms the prevailing move."""
        if not volume_data:
            return "neutral"

        ratio = volume_data.get('volume_ratio', 1.0)

        if ratio > 1.5:
            return "strong"
        if ratio < 0.7:
            return "weak"
        return "neutral"

    # ------------------------------------------------------------------ #
    # Full analysis
    # ------------------------------------------------------------------ #

    def analyze(self, df: pd.DataFrame, symbol: str = "") -> Dict:
        """Run every indicator and return the combined result."""
        if df is None or len(df) < 30:
            self.logger.warning("Not enough history for technical analysis of %s", symbol)
            return {}

        try:
            ma_data = self.get_moving_averages(df)
            rsi = self.calculate_rsi(df)
            macd_data = self.calculate_macd(df)
            bb_data = self.calculate_bollinger_bands(df)
            volume_data = self.analyze_volume(df)

            current_price = float(df['close'].iloc[-1])

            return {
                'moving_averages': ma_data,
                'rsi': rsi,
                'rsi_signal': self.get_rsi_signal(rsi),
                'macd': macd_data,
                'macd_signal': self.get_macd_signal(macd_data),
                'bollinger_bands': bb_data,
                'bollinger_signal': self.get_bollinger_signal(current_price, bb_data),
                'volume': volume_data,
                'volume_signal': self.get_volume_signal(volume_data),
            }

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Technical analysis failed for %s: %s", symbol, exc)
            return {}


if __name__ == "__main__":
    import yfinance as yf

    logging.basicConfig(level=logging.INFO)

    data = yf.Ticker('AAPL').history(period='1y', auto_adjust=True)
    data.columns = [c.lower() for c in data.columns]

    result = TechnicalAnalyzer().analyze(data, 'AAPL')
    for key, value in result.items():
        print(f"{key}: {value}")
