"""
Fundamental Analysis Module
Analyzes financial metrics: P/E ratio, ROE, Growth rates, Debt ratios, etc.
"""

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class FundamentalAnalyzer:
    """Performs fundamental analysis on stock financial data"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ==================== Valuation Metrics ====================

    @staticmethod
    def analyze_pe_ratio(pe_ratio: Optional[float]) -> Tuple[str, float]:
        """
        Analyze Price-to-Earnings ratio
        Good P/E varies by industry, typically 15-25 is reasonable

        Args:
            pe_ratio: P/E ratio value

        Returns:
            Tuple of (assessment, score 0-100)
        """
        if pe_ratio is None or pe_ratio <= 0:
            return "no_data", 50.0

        if pe_ratio < 10:
            return "very_cheap", 90.0
        elif pe_ratio < 15:
            return "cheap", 80.0
        elif pe_ratio < 25:
            return "fair", 70.0
        elif pe_ratio < 35:
            return "expensive", 40.0
        else:
            return "very_expensive", 20.0

    @staticmethod
    def analyze_roe(roe: Optional[float]) -> Tuple[str, float]:
        """
        Analyze Return on Equity
        Higher is better. > 15% is good, > 20% is excellent

        Args:
            roe: ROE percentage value

        Returns:
            Tuple of (assessment, score 0-100)
        """
        if roe is None:
            return "no_data", 50.0

        # Convert to percentage if needed
        roe = roe * 100 if roe < 1 else roe

        if roe > 25:
            return "excellent", 95.0
        elif roe > 20:
            return "very_good", 85.0
        elif roe > 15:
            return "good", 75.0
        elif roe > 10:
            return "acceptable", 60.0
        elif roe > 0:
            return "weak", 40.0
        else:
            return "poor", 10.0

    @staticmethod
    def analyze_profit_margin(margin: Optional[float]) -> Tuple[str, float]:
        """
        Analyze Net Profit Margin
        Higher is better. Varies by industry

        Args:
            margin: Profit margin as decimal (e.g., 0.15 for 15%)

        Returns:
            Tuple of (assessment, score 0-100)
        """
        if margin is None:
            return "no_data", 50.0

        # Ensure it's in percentage form
        margin = margin * 100 if margin < 1 else margin

        if margin > 20:
            return "excellent", 95.0
        elif margin > 15:
            return "very_good", 85.0
        elif margin > 10:
            return "good", 75.0
        elif margin > 5:
            return "acceptable", 60.0
        elif margin > 0:
            return "weak", 40.0
        else:
            return "poor", 10.0

    @staticmethod
    def analyze_debt_to_equity(d2e: Optional[float]) -> Tuple[str, float]:
        """
        Analyze Debt-to-Equity ratio
        Lower is better. Safe range: < 2.0, Ideal: < 1.0

        Args:
            d2e: Debt-to-Equity ratio

        Returns:
            Tuple of (assessment, score 0-100)
        """
        if d2e is None or d2e < 0:
            return "no_data", 50.0

        if d2e < 0.5:
            return "very_low", 95.0
        elif d2e < 1.0:
            return "low", 85.0
        elif d2e < 1.5:
            return "moderate", 75.0
        elif d2e < 2.0:
            return "elevated", 60.0
        elif d2e < 3.0:
            return "high", 40.0
        else:
            return "very_high", 20.0

    # ==================== Growth Metrics ====================

    @staticmethod
    def analyze_revenue_growth(growth: Optional[float]) -> Tuple[str, float]:
        """
        Analyze Revenue Growth rate
        Annual growth rate. > 10% is good for established companies

        Args:
            growth: Growth rate as decimal (e.g., 0.15 for 15%)

        Returns:
            Tuple of (assessment, score 0-100)
        """
        if growth is None:
            return "no_data", 50.0

        # Ensure it's in percentage
        growth = growth * 100 if growth < 1 and growth > -1 else growth

        if growth > 30:
            return "excellent", 95.0
        elif growth > 20:
            return "very_good", 85.0
        elif growth > 10:
            return "good", 75.0
        elif growth > 5:
            return "acceptable", 60.0
        elif growth > 0:
            return "weak", 40.0
        else:
            return "negative", 20.0

    @staticmethod
    def analyze_earnings_growth(growth: Optional[float]) -> Tuple[str, float]:
        """
        Analyze Earnings Growth rate
        Earnings growth should match or exceed revenue growth

        Args:
            growth: Growth rate as decimal

        Returns:
            Tuple of (assessment, score 0-100)
        """
        if growth is None:
            return "no_data", 50.0

        growth = growth * 100 if growth < 1 and growth > -1 else growth

        if growth > 30:
            return "excellent", 95.0
        elif growth > 20:
            return "very_good", 85.0
        elif growth > 15:
            return "good", 75.0
        elif growth > 10:
            return "acceptable", 60.0
        elif growth > 0:
            return "weak", 40.0
        else:
            return "negative", 20.0

    # ==================== Dividend Analysis ====================

    @staticmethod
    def analyze_dividend_yield(yield_pct: Optional[float]) -> Tuple[str, float]:
        """
        Analyze Dividend Yield
        Average is 2-3%, higher yields can indicate value stocks

        Args:
            yield_pct: Dividend yield as decimal (e.g., 0.03 for 3%)

        Returns:
            Tuple of (assessment, score 0-100)
        """
        if yield_pct is None or yield_pct < 0:
            return "no_yield", 50.0

        yield_pct = yield_pct * 100 if yield_pct < 1 else yield_pct

        if yield_pct > 8:
            return "very_high", 70.0
        elif yield_pct > 5:
            return "high", 75.0
        elif yield_pct > 3:
            return "good", 70.0
        elif yield_pct > 2:
            return "fair", 65.0
        elif yield_pct > 0.5:
            return "low", 55.0
        else:
            return "no_yield", 50.0

    # ==================== Complete Fundamental Analysis ====================

    def analyze(self, fundamental_data: Dict) -> Dict:
        """
        Perform complete fundamental analysis

        Args:
            fundamental_data: Dictionary with financial metrics from yfinance

        Returns:
            Dictionary with analyzed metrics and overall score
        """
        if not fundamental_data:
            self.logger.warning("No fundamental data provided")
            return {}

        try:
            symbol = fundamental_data.get('symbol', 'UNKNOWN')

            # Valuation metrics
            pe_ratio = fundamental_data.get('pe_ratio')
            pe_assessment, pe_score = self.analyze_pe_ratio(pe_ratio)

            roe = fundamental_data.get('roe')
            roe_assessment, roe_score = self.analyze_roe(roe)

            profit_margin = fundamental_data.get('profit_margin')
            margin_assessment, margin_score = self.analyze_profit_margin(profit_margin)

            d2e = fundamental_data.get('debt_to_equity')
            d2e_assessment, d2e_score = self.analyze_debt_to_equity(d2e)

            # Growth metrics
            revenue_growth = fundamental_data.get('revenue_growth')
            rev_growth_assessment, rev_growth_score = self.analyze_revenue_growth(revenue_growth)

            earnings_growth = fundamental_data.get('earnings_growth')
            earn_growth_assessment, earn_growth_score = self.analyze_earnings_growth(earnings_growth)

            # Dividend
            div_yield = fundamental_data.get('dividend_yield')
            div_assessment, div_score = self.analyze_dividend_yield(div_yield)

            # Calculate overall fundamental score
            scores = [pe_score, roe_score, margin_score, d2e_score, rev_growth_score, earn_growth_score, div_score]
            scores = [s for s in scores if s is not None]  # Remove None values
            fundamental_score = sum(scores) / len(scores) if scores else 50.0

            return {
                'symbol': symbol,
                'pe_ratio': {
                    'value': pe_ratio,
                    'assessment': pe_assessment,
                    'score': pe_score
                },
                'roe': {
                    'value': roe,
                    'assessment': roe_assessment,
                    'score': roe_score
                },
                'profit_margin': {
                    'value': profit_margin,
                    'assessment': margin_assessment,
                    'score': margin_score
                },
                'debt_to_equity': {
                    'value': d2e,
                    'assessment': d2e_assessment,
                    'score': d2e_score
                },
                'revenue_growth': {
                    'value': revenue_growth,
                    'assessment': rev_growth_assessment,
                    'score': rev_growth_score
                },
                'earnings_growth': {
                    'value': earnings_growth,
                    'assessment': earn_growth_assessment,
                    'score': earn_growth_score
                },
                'dividend_yield': {
                    'value': div_yield,
                    'assessment': div_assessment,
                    'score': div_score
                },
                'overall_score': round(fundamental_score, 2),
                'sector': fundamental_data.get('sector'),
                'industry': fundamental_data.get('industry'),
            }

        except Exception as e:
            self.logger.error(f"Error in fundamental analysis: {str(e)}")
            return {}


# Example usage
if __name__ == "__main__":
    import yfinance as yf

    logging.basicConfig(level=logging.INFO)

    analyzer = FundamentalAnalyzer()

    # Fetch fundamental data
    print("Fetching AAPL fundamental data...")
    ticker = yf.Ticker('AAPL')
    info = ticker.info

    fundamental_data = {
        'symbol': 'AAPL',
        'pe_ratio': info.get('trailingPE'),
        'roe': info.get('returnOnEquity'),
        'profit_margin': info.get('profitMargins'),
        'debt_to_equity': info.get('debtToEquity'),
        'revenue_growth': info.get('revenueGrowth'),
        'earnings_growth': info.get('earningsGrowth'),
        'dividend_yield': info.get('dividendYield'),
        'sector': info.get('sector'),
        'industry': info.get('industry'),
    }

    # Analyze
    print("\nPerforming fundamental analysis...")
    result = analyzer.analyze(fundamental_data)

    print(f"\nP/E Ratio: {result['pe_ratio']}")
    print(f"ROE: {result['roe']}")
    print(f"Profit Margin: {result['profit_margin']}")
    print(f"Debt-to-Equity: {result['debt_to_equity']}")
    print(f"Revenue Growth: {result['revenue_growth']}")
    print(f"Earnings Growth: {result['earnings_growth']}")
    print(f"Dividend Yield: {result['dividend_yield']}")
    print(f"\nOverall Fundamental Score: {result['overall_score']}/100") 
