"""
Scoring Module
Combines technical, fundamental, and sentiment scores to generate a unified score (0-100)
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StockScorer:
    """Scores stocks based on multiple analysis dimensions"""

    # Default weights (can be customized)
    WEIGHTS = {
        'technical': 0.40,  # 40%
        'fundamental': 0.35,  # 35%
        'sentiment': 0.25,   # 25%
    }

    # Signal to score mapping
    SIGNAL_SCORES = {
        'strong_buy': 95,
        'buy': 75,
        'neutral': 50,
        'sell': 25,
        'strong_sell': 5,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize scorer with optional custom weights

        Args:
            weights: Dictionary with 'technical', 'fundamental', 'sentiment' weights
        """
        self.logger = logging.getLogger(__name__)
        if weights:
            self.WEIGHTS = weights

        # Verify weights sum to 1.0
        total = sum(self.WEIGHTS.values())
        if abs(total - 1.0) > 0.01:
            self.logger.warning(f"Weights don't sum to 1.0 (sum={total}), normalizing...")
            for key in self.WEIGHTS:
                self.WEIGHTS[key] = self.WEIGHTS[key] / total

    # ==================== Technical Score ====================

    def calculate_technical_score(self, technical_data: Dict) -> float:
        """
        Calculate technical analysis score (0-100)
        Based on moving averages, RSI, MACD, Bollinger Bands, Volume

        Args:
            technical_data: Dictionary with technical indicators

        Returns:
            Score 0-100
        """
        if not technical_data:
            return 50.0

        try:
            scores = []
            weights = []

            # Moving averages trend (20% of technical score)
            ma_data = technical_data.get('moving_averages', {})
            if ma_data:
                trend = ma_data.get('trend', 'neutral')
                if trend == 'strong_uptrend':
                    ma_score = 90.0
                elif trend == 'uptrend':
                    ma_score = 70.0
                elif trend == 'neutral':
                    ma_score = 50.0
                elif trend == 'downtrend':
                    ma_score = 30.0
                else:
                    ma_score = 10.0

                scores.append(ma_score)
                weights.append(0.20)

            # RSI (20% of technical score)
            rsi = technical_data.get('rsi')
            if rsi is not None:
                if rsi < 30:
                    rsi_score = 75.0
                elif rsi < 45:
                    rsi_score = 70.0
                elif rsi < 55:
                    rsi_score = 50.0
                elif rsi < 70:
                    rsi_score = 30.0
                else:
                    rsi_score = 20.0

                scores.append(rsi_score)
                weights.append(0.20)

            # MACD signal (20% of technical score)
            macd_signal = technical_data.get('macd_signal', 'neutral')
            macd_score = self.SIGNAL_SCORES.get(macd_signal, 50)
            scores.append(macd_score)
            weights.append(0.20)

            # Bollinger Bands signal (20% of technical score)
            bb_signal = technical_data.get('bollinger_signal', 'neutral')
            bb_score = self.SIGNAL_SCORES.get(bb_signal, 50)
            scores.append(bb_score)
            weights.append(0.20)

            # Volume signal (20% of technical score)
            volume_signal = technical_data.get('volume_signal', 'neutral')
            if volume_signal == 'strong':
                volume_score = 75.0
            elif volume_signal == 'weak':
                volume_score = 30.0
            else:
                volume_score = 50.0
            scores.append(volume_score)
            weights.append(0.20)

            # Calculate weighted average
            if scores:
                technical_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights) if sum(weights) > 0 else 50.0
            else:
                technical_score = 50.0

            return round(technical_score, 2)

        except Exception as e:
            self.logger.error(f"Error calculating technical score: {str(e)}")
            return 50.0

    # ==================== Fundamental Score ====================

    def calculate_fundamental_score(self, fundamental_data: Dict) -> float:
        """
        Calculate fundamental analysis score (0-100)
        Based on P/E, ROE, margins, growth, debt

        Args:
            fundamental_data: Dictionary with fundamental metrics

        Returns:
            Score 0-100
        """
        if not fundamental_data:
            return 50.0

        try:
            scores = []

            # Extract individual metric scores
            for metric in ['pe_ratio', 'roe', 'profit_margin', 'debt_to_equity',
                          'revenue_growth', 'earnings_growth', 'dividend_yield']:
                metric_data = fundamental_data.get(metric, {})
                if isinstance(metric_data, dict) and 'score' in metric_data:
                    scores.append(metric_data['score'])

            # Calculate average
            if scores:
                fundamental_score = sum(scores) / len(scores)
            else:
                fundamental_score = fundamental_data.get('overall_score', 50.0)

            return round(fundamental_score, 2)

        except Exception as e:
            self.logger.error(f"Error calculating fundamental score: {str(e)}")
            return 50.0

    # ==================== Sentiment Score ====================

    def calculate_sentiment_score(self, news_sentiment: Dict) -> float:
        """
        Calculate sentiment score based on recent news

        Args:
            news_sentiment: Dictionary with news data and sentiment scores

        Returns:
            Score 0-100
        """
        if not news_sentiment:
            return 50.0

        try:
            sentiments = news_sentiment.get('sentiments', [])

            if not sentiments:
                return 50.0

            # Score each sentiment: positive (75), neutral (50), negative (25)
            sentiment_scores = {
                'positive': 75,
                'neutral': 50,
                'negative': 25,
            }

            scores = [sentiment_scores.get(s, 50) for s in sentiments]
            sentiment_score = sum(scores) / len(scores)

            return round(sentiment_score, 2)

        except Exception as e:
            self.logger.error(f"Error calculating sentiment score: {str(e)}")
            return 50.0

    # ==================== Overall Score ====================

    def calculate_overall_score(self,
                               technical_score: float = 50.0,
                               fundamental_score: float = 50.0,
                               sentiment_score: float = 50.0) -> float:
        """
        Calculate overall investment score

        Args:
            technical_score: Technical analysis score (0-100)
            fundamental_score: Fundamental analysis score (0-100)
            sentiment_score: Sentiment analysis score (0-100)

        Returns:
            Overall score (0-100)
        """
        try:
            overall = (
                technical_score * self.WEIGHTS['technical'] +
                fundamental_score * self.WEIGHTS['fundamental'] +
                sentiment_score * self.WEIGHTS['sentiment']
            )

            return round(overall, 2)

        except Exception as e:
            self.logger.error(f"Error calculating overall score: {str(e)}")
            return 50.0

    # ==================== Full Analysis ====================

    def score(self,
             technical_data: Dict,
             fundamental_data: Dict,
             news_sentiment: Optional[Dict] = None) -> Dict:
        """
        Perform complete scoring analysis

        Args:
            technical_data: Technical analysis results
            fundamental_data: Fundamental analysis results
            news_sentiment: News sentiment data (optional)

        Returns:
            Dictionary with all scores
        """
        try:
            # Calculate individual scores
            tech_score = self.calculate_technical_score(technical_data)
            fund_score = self.calculate_fundamental_score(fundamental_data)
            sent_score = self.calculate_sentiment_score(news_sentiment or {})

            # Calculate overall score
            overall_score = self.calculate_overall_score(tech_score, fund_score, sent_score)

            return {
                'technical_score': tech_score,
                'fundamental_score': fund_score,
                'sentiment_score': sent_score,
                'overall_score': overall_score,
                'weights': self.WEIGHTS,
            }

        except Exception as e:
            self.logger.error(f"Error in scoring: {str(e)}")
            return {
                'technical_score': 50.0,
                'fundamental_score': 50.0,
                'sentiment_score': 50.0,
                'overall_score': 50.0,
                'weights': self.WEIGHTS,
            }

    # ==================== Score Rating ====================

    @staticmethod
    def get_rating(score: float) -> str:
        """
        Get investment rating from overall score

        Args:
            score: Overall score (0-100)

        Returns:
            Rating string
        """
        if score >= 80:
            return "STRONG BUY"
        elif score >= 65:
            return "BUY"
        elif score >= 50:
            return "HOLD"
        elif score >= 35:
            return "SELL"
        else:
            return "STRONG SELL"


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    scorer = StockScorer()

    # Example data
    technical_data = {
        'moving_averages': {'trend': 'uptrend'},
        'rsi': 55,
        'macd_signal': 'buy',
        'bollinger_signal': 'buy',
        'volume_signal': 'strong',
    }

    fundamental_data = {
        'pe_ratio': {'score': 75},
        'roe': {'score': 85},
        'profit_margin': {'score': 70},
        'debt_to_equity': {'score': 80},
        'revenue_growth': {'score': 75},
        'earnings_growth': {'score': 80},
        'dividend_yield': {'score': 65},
        'overall_score': 75,
    }

    news_sentiment = {
        'sentiments': ['positive', 'positive', 'neutral'],
    }

    # Score
    result = scorer.score(technical_data, fundamental_data, news_sentiment)

    print(f"Technical Score: {result['technical_score']}")
    print(f"Fundamental Score: {result['fundamental_score']}")
    print(f"Sentiment Score: {result['sentiment_score']}")
    print(f"Overall Score: {result['overall_score']}")
    print(f"Rating: {scorer.get_rating(result['overall_score'])}") 
