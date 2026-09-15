"""
Scoring Module
Combines the technical, fundamental and sentiment scores into one 0-100 score.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StockScorer:
    """Blends the analysis dimensions into a single investment score."""

    DEFAULT_WEIGHTS = {
        'technical': 0.40,
        'fundamental': 0.35,
        'sentiment': 0.25,
    }

    SIGNAL_SCORES = {
        'strong_buy': 95.0,
        'buy': 75.0,
        'neutral': 50.0,
        'sell': 25.0,
        'strong_sell': 5.0,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Args:
            weights: Optional override. Accepts either the short keys
                ('technical') or the config.yml style keys
                ('technical_weight'); both spellings are understood.
        """
        self.logger = logging.getLogger(__name__)
        # Copy, so the class-level defaults are never mutated.
        self.weights = dict(self.DEFAULT_WEIGHTS)

        if weights:
            for name in self.DEFAULT_WEIGHTS:
                # config.yml uses "technical_weight"; accept "technical" too.
                value = weights.get(f"{name}_weight", weights.get(name))
                if value is not None:
                    try:
                        self.weights[name] = float(value)
                    except (TypeError, ValueError):
                        self.logger.warning(
                            "Ignoring non-numeric weight for %s: %r", name, value)

        total = sum(self.weights.values())
        if total <= 0:
            self.logger.warning("Weights sum to zero, falling back to defaults")
            self.weights = dict(self.DEFAULT_WEIGHTS)
        elif abs(total - 1.0) > 0.01:
            self.logger.info("Normalising weights (sum was %.3f)", total)
            self.weights = {k: v / total for k, v in self.weights.items()}

    # Backwards-compatible alias for older code that referenced WEIGHTS.
    @property
    def WEIGHTS(self) -> Dict[str, float]:  # noqa: N802 - kept for compatibility
        return self.weights

    # ------------------------------------------------------------------ #
    # Technical
    # ------------------------------------------------------------------ #

    def calculate_technical_score(self, technical_data: Dict) -> float:
        """Weighted blend of the trend, RSI, MACD, Bollinger and volume signals."""
        if not technical_data:
            return 50.0

        try:
            scores, weights = [], []

            trend_scores = {
                'strong_uptrend': 90.0,
                'uptrend': 70.0,
                'neutral': 50.0,
                'downtrend': 30.0,
                'strong_downtrend': 10.0,
            }
            ma_data = technical_data.get('moving_averages') or {}
            if ma_data:
                scores.append(trend_scores.get(ma_data.get('trend'), 50.0))
                weights.append(0.25)

            rsi = technical_data.get('rsi')
            if rsi is not None:
                if rsi < 30:
                    rsi_score = 85.0       # oversold, a bounce is likely
                elif rsi < 45:
                    rsi_score = 70.0
                elif rsi < 55:
                    rsi_score = 50.0
                elif rsi < 70:
                    rsi_score = 35.0
                else:
                    rsi_score = 15.0       # overbought
                scores.append(rsi_score)
                weights.append(0.25)

            if technical_data.get('macd'):
                scores.append(self.SIGNAL_SCORES.get(
                    technical_data.get('macd_signal'), 50.0))
                weights.append(0.20)

            if technical_data.get('bollinger_bands'):
                scores.append(self.SIGNAL_SCORES.get(
                    technical_data.get('bollinger_signal'), 50.0))
                weights.append(0.15)

            if technical_data.get('volume'):
                volume_scores = {'strong': 70.0, 'weak': 35.0, 'neutral': 50.0}
                scores.append(volume_scores.get(
                    technical_data.get('volume_signal'), 50.0))
                weights.append(0.15)

            if not scores:
                return 50.0

            total_weight = sum(weights)
            blended = sum(s * w for s, w in zip(scores, weights)) / total_weight
            return round(blended, 2)

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Technical scoring failed: %s", exc)
            return 50.0

    # ------------------------------------------------------------------ #
    # Fundamental
    # ------------------------------------------------------------------ #

    def calculate_fundamental_score(self, fundamental_data: Dict) -> float:
        """Average of the fundamental metrics that actually had data."""
        if not fundamental_data:
            return 50.0

        try:
            scores = []
            for metric in ('pe_ratio', 'roe', 'profit_margin', 'debt_to_equity',
                           'revenue_growth', 'earnings_growth', 'dividend_yield'):
                entry = fundamental_data.get(metric)
                if isinstance(entry, dict) and entry.get('score') is not None:
                    scores.append(float(entry['score']))

            if scores:
                return round(sum(scores) / len(scores), 2)

            return float(fundamental_data.get('overall_score', 50.0))

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Fundamental scoring failed: %s", exc)
            return 50.0

    # ------------------------------------------------------------------ #
    # Sentiment
    # ------------------------------------------------------------------ #

    def calculate_sentiment_score(self, news_sentiment: Optional[Dict]) -> float:
        """
        Score recent news sentiment.

        No news source is wired up yet, so this returns a neutral 50 and the
        weighting simply spreads across the other two dimensions.
        """
        if not news_sentiment:
            return 50.0

        try:
            sentiments = news_sentiment.get('sentiments') or []
            if not sentiments:
                return 50.0

            mapping = {'positive': 75.0, 'neutral': 50.0, 'negative': 25.0}
            scores = [mapping.get(s, 50.0) for s in sentiments]
            return round(sum(scores) / len(scores), 2)

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Sentiment scoring failed: %s", exc)
            return 50.0

    # ------------------------------------------------------------------ #
    # Overall
    # ------------------------------------------------------------------ #

    def calculate_overall_score(self, technical_score: float = 50.0,
                                fundamental_score: float = 50.0,
                                sentiment_score: float = 50.0) -> float:
        """Weighted combination of the three dimensions."""
        try:
            overall = (
                technical_score * self.weights['technical']
                + fundamental_score * self.weights['fundamental']
                + sentiment_score * self.weights['sentiment']
            )
            return round(overall, 2)
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Overall scoring failed: %s", exc)
            return 50.0

    def score(self, technical_data: Dict, fundamental_data: Dict,
              news_sentiment: Optional[Dict] = None) -> Dict:
        """Run the full scoring pipeline for one stock."""
        technical_score = self.calculate_technical_score(technical_data)
        fundamental_score = self.calculate_fundamental_score(fundamental_data)
        sentiment_score = self.calculate_sentiment_score(news_sentiment)

        return {
            'technical_score': technical_score,
            'fundamental_score': fundamental_score,
            'sentiment_score': sentiment_score,
            'overall_score': self.calculate_overall_score(
                technical_score, fundamental_score, sentiment_score),
            'weights': dict(self.weights),
        }

    @staticmethod
    def get_rating(score: float) -> str:
        """Map an overall score onto an action label."""
        if score >= 80:
            return "STRONG BUY"
        if score >= 65:
            return "BUY"
        if score >= 50:
            return "HOLD"
        if score >= 35:
            return "SELL"
        return "STRONG SELL"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Exercise the config.yml style keys, which used to raise a KeyError.
    scorer = StockScorer(weights={
        'technical_weight': 0.40,
        'fundamental_weight': 0.35,
        'sentiment_weight': 0.25,
    })

    technical = {
        'moving_averages': {'trend': 'uptrend'},
        'rsi': 42,
        'macd': {'macd': 1.0, 'signal': 0.5, 'histogram': 0.5},
        'macd_signal': 'buy',
        'bollinger_bands': {'upper': 110, 'middle': 100, 'lower': 90},
        'bollinger_signal': 'buy',
        'volume': {'volume_ratio': 1.8},
        'volume_signal': 'strong',
    }
    fundamental = {
        'pe_ratio': {'score': 75.0},
        'roe': {'score': 85.0},
        'profit_margin': {'score': 75.0},
        'debt_to_equity': {'score': 85.0},
        'revenue_growth': {'score': 75.0},
        'earnings_growth': {'score': 85.0},
        'dividend_yield': {'score': None},
    }

    out = scorer.score(technical, fundamental)
    print(out)
    print("Rating:", StockScorer.get_rating(out['overall_score']))
