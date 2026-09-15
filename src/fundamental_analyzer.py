"""
Fundamental Analysis Module
Scores financial metrics: P/E, ROE, margins, debt, growth and dividend yield.
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Marker used when a metric is missing so it can be excluded from the average.
NO_DATA = "no_data"


def _fraction_to_percent(value: Optional[float]) -> Optional[float]:
    """
    Convert a yfinance fraction into a percentage.

    returnOnEquity, profitMargins, revenueGrowth and earningsGrowth are always
    fractions, so they are always multiplied by 100. Do not try to guess based
    on magnitude: Apple's ROE arrives as 1.4875, meaning 148.75%, and any
    "is it less than 1" test would read that as 1.49% and grade a world-class
    company as weak.
    """
    if value is None:
        return None
    try:
        return float(value) * 100.0
    except (TypeError, ValueError):
        return None


def _already_percent(value: Optional[float]) -> Optional[float]:
    """Pass through a value that yfinance already expresses as a percentage."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class FundamentalAnalyzer:
    """Scores a company's financial metrics on a 0-100 scale."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------ #
    # Valuation
    # ------------------------------------------------------------------ #

    @staticmethod
    def analyze_pe_ratio(pe_ratio: Optional[float]) -> Tuple[str, Optional[float]]:
        """Price-to-earnings. A negative P/E means the company is loss-making."""
        if pe_ratio is None:
            return NO_DATA, None

        try:
            pe_ratio = float(pe_ratio)
        except (TypeError, ValueError):
            return NO_DATA, None

        if pe_ratio <= 0:
            return "loss_making", 25.0
        if pe_ratio < 10:
            return "very_cheap", 90.0
        if pe_ratio < 15:
            return "cheap", 80.0
        if pe_ratio < 25:
            return "fair", 70.0
        if pe_ratio < 35:
            return "expensive", 40.0
        return "very_expensive", 20.0

    @staticmethod
    def analyze_roe(roe: Optional[float]) -> Tuple[str, Optional[float]]:
        """Return on equity. Above 15% is good, above 25% excellent."""
        roe = _fraction_to_percent(roe)
        if roe is None:
            return NO_DATA, None

        if roe > 25:
            return "excellent", 95.0
        if roe > 20:
            return "very_good", 85.0
        if roe > 15:
            return "good", 75.0
        if roe > 10:
            return "acceptable", 60.0
        if roe > 0:
            return "weak", 40.0
        return "poor", 10.0

    @staticmethod
    def analyze_profit_margin(margin: Optional[float]) -> Tuple[str, Optional[float]]:
        """Net profit margin."""
        margin = _fraction_to_percent(margin)
        if margin is None:
            return NO_DATA, None

        if margin > 20:
            return "excellent", 95.0
        if margin > 15:
            return "very_good", 85.0
        if margin > 10:
            return "good", 75.0
        if margin > 5:
            return "acceptable", 60.0
        if margin > 0:
            return "weak", 40.0
        return "poor", 10.0

    @staticmethod
    def analyze_debt_to_equity(d2e: Optional[float]) -> Tuple[str, Optional[float]]:
        """
        Debt-to-equity ratio. Lower is safer.

        yfinance reports this as a percentage (145.0 means a ratio of 1.45),
        so anything above 5 is rescaled before being graded.
        """
        if d2e is None:
            return NO_DATA, None

        try:
            d2e = float(d2e)
        except (TypeError, ValueError):
            return NO_DATA, None

        if d2e < 0:
            return NO_DATA, None

        if d2e > 5:
            d2e = d2e / 100.0

        if d2e < 0.5:
            return "very_low", 95.0
        if d2e < 1.0:
            return "low", 85.0
        if d2e < 1.5:
            return "moderate", 75.0
        if d2e < 2.0:
            return "elevated", 60.0
        if d2e < 3.0:
            return "high", 40.0
        return "very_high", 20.0

    # ------------------------------------------------------------------ #
    # Growth
    # ------------------------------------------------------------------ #

    @staticmethod
    def analyze_revenue_growth(growth: Optional[float]) -> Tuple[str, Optional[float]]:
        """Year-on-year revenue growth."""
        growth = _fraction_to_percent(growth)
        if growth is None:
            return NO_DATA, None

        if growth > 30:
            return "excellent", 95.0
        if growth > 20:
            return "very_good", 85.0
        if growth > 10:
            return "good", 75.0
        if growth > 5:
            return "acceptable", 60.0
        if growth > 0:
            return "weak", 40.0
        return "negative", 20.0

    @staticmethod
    def analyze_earnings_growth(growth: Optional[float]) -> Tuple[str, Optional[float]]:
        """Year-on-year earnings growth."""
        growth = _fraction_to_percent(growth)
        if growth is None:
            return NO_DATA, None

        if growth > 30:
            return "excellent", 95.0
        if growth > 20:
            return "very_good", 85.0
        if growth > 15:
            return "good", 75.0
        if growth > 10:
            return "acceptable", 60.0
        if growth > 0:
            return "weak", 40.0
        return "negative", 20.0

    # ------------------------------------------------------------------ #
    # Dividend
    # ------------------------------------------------------------------ #

    @staticmethod
    def analyze_dividend_yield(yield_pct: Optional[float]) -> Tuple[str, Optional[float]]:
        """
        Dividend yield.

        The value is expected already as a percentage (3.0 meaning 3%); the
        data fetcher normalises it from the dividend rate and price, because
        yfinance's own dividendYield field has meant a fraction in some
        versions and a percentage in others.

        A missing or zero yield is not a negative signal (growth companies
        often pay nothing), so it is reported without a score.
        """
        yield_pct = _already_percent(yield_pct)
        if yield_pct is None or yield_pct <= 0:
            return "no_dividend", None

        if yield_pct > 10:
            return "suspiciously_high", 55.0
        if yield_pct > 5:
            return "high", 80.0
        if yield_pct > 3:
            return "good", 75.0
        if yield_pct > 1.5:
            return "fair", 65.0
        return "low", 55.0

    # ------------------------------------------------------------------ #
    # Full analysis
    # ------------------------------------------------------------------ #

    def analyze(self, fundamental_data: Dict) -> Dict:
        """
        Score every available metric.

        Metrics without data are excluded from the average rather than being
        counted as neutral, so a company with two strong figures is not
        dragged down to 50 by five missing ones.
        """
        if not fundamental_data:
            return {}

        try:
            symbol = fundamental_data.get('symbol', 'UNKNOWN')

            metrics = {
                'pe_ratio': self.analyze_pe_ratio(fundamental_data.get('pe_ratio')),
                'roe': self.analyze_roe(fundamental_data.get('roe')),
                'profit_margin': self.analyze_profit_margin(
                    fundamental_data.get('profit_margin')),
                'debt_to_equity': self.analyze_debt_to_equity(
                    fundamental_data.get('debt_to_equity')),
                'revenue_growth': self.analyze_revenue_growth(
                    fundamental_data.get('revenue_growth')),
                'earnings_growth': self.analyze_earnings_growth(
                    fundamental_data.get('earnings_growth')),
                'dividend_yield': self.analyze_dividend_yield(
                    fundamental_data.get('dividend_yield')),
            }

            result: Dict = {
                'symbol': symbol,
                'sector': fundamental_data.get('sector'),
                'industry': fundamental_data.get('industry'),
            }

            available_scores = []
            for name, (assessment, score) in metrics.items():
                result[name] = {
                    'value': fundamental_data.get(name),
                    'assessment': assessment,
                    'score': score,
                }
                if score is not None:
                    available_scores.append(score)

            if available_scores:
                result['overall_score'] = round(
                    sum(available_scores) / len(available_scores), 2)
                result['metrics_available'] = len(available_scores)
            else:
                result['overall_score'] = 50.0
                result['metrics_available'] = 0

            return result

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Fundamental analysis failed: %s", exc)
            return {}


if __name__ == "__main__":
    import yfinance as yf

    logging.basicConfig(level=logging.INFO)

    info = yf.Ticker('AAPL').info
    payload = {
        'symbol': 'AAPL',
        'pe_ratio': info.get('trailingPE'),
        'roe': info.get('returnOnEquity'),
        'profit_margin': info.get('profitMargins'),
        'debt_to_equity': info.get('debtToEquity'),
        'revenue_growth': info.get('revenueGrowth'),
        'earnings_growth': info.get('earningsGrowth'),
        'dividend_yield': info.get('dividendYield'),
    }

    out = FundamentalAnalyzer().analyze(payload)
    for key, value in out.items():
        print(f"{key}: {value}")
