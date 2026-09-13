"""
Recommendation Module
Generates buy/sell recommendations with entry prices, stop loss, and profit targets
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StockRecommender:
    """Generates investment recommendations based on scores"""

    def __init__(self,
                 stop_loss_percent: float = 3.0,
                 take_profit_percent: float = 15.0):
        """
        Initialize recommender

        Args:
            stop_loss_percent: Default stop loss percentage (e.g., 3.0 for 3%)
            take_profit_percent: Default take profit percentage (e.g., 15.0 for 15%)
        """
        self.logger = logging.getLogger(__name__)
        self.stop_loss_percent = stop_loss_percent
        self.take_profit_percent = take_profit_percent

    # ==================== Recommendation Logic ====================

    def generate_recommendation(self,
                               symbol: str,
                               current_price: float,
                               overall_score: float,
                               technical_data: Dict,
                               fundamental_data: Dict) -> Dict:
        """
        Generate investment recommendation

        Args:
            symbol: Stock symbol
            current_price: Current stock price
            overall_score: Overall investment score (0-100)
            technical_data: Technical analysis data
            fundamental_data: Fundamental analysis data

        Returns:
            Dictionary with recommendation
        """
        try:
            # Determine action based on score
            if overall_score >= 80:
                action = "STRONG BUY"
                confidence = 0.95
                stop_loss_percent = 2.0  # Tighter stop for strong signals
                take_profit_percent = 20.0
            elif overall_score >= 65:
                action = "BUY"
                confidence = 0.80
                stop_loss_percent = self.stop_loss_percent
                take_profit_percent = self.take_profit_percent
            elif overall_score >= 50:
                action = "HOLD"
                confidence = 0.50
                stop_loss_percent = 0
                take_profit_percent = 0
            elif overall_score >= 35:
                action = "SELL"
                confidence = 0.70
                stop_loss_percent = 0
                take_profit_percent = 0
            else:
                action = "STRONG SELL"
                confidence = 0.90
                stop_loss_percent = 0
                take_profit_percent = 0

            # Calculate prices
            entry_price = current_price
            stop_loss = round(entry_price * (1 - stop_loss_percent / 100), 2) if stop_loss_percent > 0 else None
            target_price = round(entry_price * (1 + take_profit_percent / 100), 2) if take_profit_percent > 0 else None

            # Risk/Reward ratio
            if stop_loss and target_price:
                risk = entry_price - stop_loss
                reward = target_price - entry_price
                risk_reward_ratio = reward / risk if risk > 0 else 0
            else:
                risk_reward_ratio = 0

            # Generate reasoning
            reasons = self._generate_reasons(overall_score, technical_data, fundamental_data)

            return {
                'symbol': symbol,
                'action': action,
                'confidence': round(confidence, 2),
                'overall_score': overall_score,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target_price': target_price,
                'risk_reward_ratio': round(risk_reward_ratio, 2),
                'reasons': reasons,
                'timeframe': 'medium-term (2-6 months)',
            }

        except Exception as e:
            self.logger.error(f"Error generating recommendation for {symbol}: {str(e)}")
            return self._default_recommendation(symbol, current_price)

    # ==================== Reasoning ====================

    @staticmethod
    def _generate_reasons(overall_score: float,
                         technical_data: Dict,
                         fundamental_data: Dict) -> list:
        """
        Generate reasons for the recommendation

        Args:
            overall_score: Overall investment score
            technical_data: Technical analysis data
            fundamental_data: Fundamental analysis data

        Returns:
            List of reason strings
        """
        reasons = []

        # Technical reasons
        ma_data = technical_data.get('moving_averages', {})
        if ma_data:
            trend = ma_data.get('trend')
            if trend == 'strong_uptrend':
                reasons.append("Strong uptrend confirmed by moving averages")
            elif trend == 'uptrend':
                reasons.append("Uptrend identified by moving averages")
            elif trend == 'downtrend':
                reasons.append("Downtrend identified by moving averages")

        rsi = technical_data.get('rsi')
        if rsi is not None:
            if rsi < 30:
                reasons.append(f"Oversold signal (RSI: {rsi})")
            elif rsi > 70:
                reasons.append(f"Overbought signal (RSI: {rsi})")

        macd_signal = technical_data.get('macd_signal')
        if macd_signal == 'buy':
            reasons.append("MACD crossover generates buy signal")
        elif macd_signal == 'sell':
            reasons.append("MACD crossover generates sell signal")

        # Fundamental reasons
        pe_data = fundamental_data.get('pe_ratio', {})
        if pe_data:
            assessment = pe_data.get('assessment')
            if assessment == 'cheap' or assessment == 'very_cheap':
                reasons.append(f"P/E ratio is {assessment} - attractive valuation")
            elif assessment == 'expensive' or assessment == 'very_expensive':
                reasons.append(f"P/E ratio is {assessment} - be cautious on valuation")

        roe_data = fundamental_data.get('roe', {})
        if roe_data:
            score = roe_data.get('score', 50)
            if score >= 80:
                reasons.append("Strong ROE indicates efficient profit generation")

        growth_data = fundamental_data.get('revenue_growth', {})
        if growth_data:
            assessment = growth_data.get('assessment')
            if assessment in ['excellent', 'very_good', 'good']:
                reasons.append(f"Revenue growth is {assessment}")

        debt_data = fundamental_data.get('debt_to_equity', {})
        if debt_data:
            assessment = debt_data.get('assessment')
            if assessment in ['very_low', 'low']:
                reasons.append("Strong balance sheet with low debt")
            elif assessment in ['high', 'very_high']:
                reasons.append("High debt levels - monitor financial health")

        # Score-based reasoning
        if overall_score >= 80:
            reasons.append("Multiple indicators align for strong buy signal")
        elif overall_score < 35:
            reasons.append("Multiple indicators suggest weakness or overvaluation")

        return reasons if reasons else ["Neutral signal from all indicators"]

    # ==================== Default Recommendation ====================

    @staticmethod
    def _default_recommendation(symbol: str, current_price: float) -> Dict:
        """
        Return default recommendation when analysis fails

        Args:
            symbol: Stock symbol
            current_price: Current price

        Returns:
            Default recommendation
        """
        return {
            'symbol': symbol,
            'action': 'HOLD',
            'confidence': 0.0,
            'overall_score': 50.0,
            'entry_price': current_price,
            'stop_loss': None,
            'target_price': None,
            'risk_reward_ratio': 0,
            'reasons': ["Insufficient data for analysis"],
            'timeframe': 'N/A',
        }

    # ==================== Recommendation Summary ====================

    @staticmethod
    def format_recommendation(recommendation: Dict) -> str:
        """
        Format recommendation for display/output

        Args:
            recommendation: Recommendation dictionary

        Returns:
            Formatted string
        """
        symbol = recommendation.get('symbol', 'N/A')
        action = recommendation.get('action', 'N/A')
        score = recommendation.get('overall_score', 0)
        confidence = recommendation.get('confidence', 0)
        entry = recommendation.get('entry_price', 0)
        stop_loss = recommendation.get('stop_loss')
        target = recommendation.get('target_price')
        ratio = recommendation.get('risk_reward_ratio', 0)
        reasons = recommendation.get('reasons', [])

        text = f"""
╔══════════════════════════════════════════════════════╗
║  {symbol}: {action}
╠══════════════════════════════════════════════════════╣
║  Score: {score}/100 | Confidence: {confidence*100:.0f}%
║  Entry Price: ${entry:.2f}
"""

        if stop_loss:
            text += f"║  Stop Loss: ${stop_loss:.2f} ({(stop_loss/entry - 1)*100:.1f}%)\n"

        if target:
            text += f"║  Target Price: ${target:.2f} ({(target/entry - 1)*100:.1f}%)\n"

        if ratio > 0:
            text += f"║  Risk/Reward Ratio: {ratio:.2f}:1\n"

        text += "╠══════════════════════════════════════════════════════╣\n"
        text += "║  Reasons:\n"

        for reason in reasons:
            text += f"║  • {reason}\n"

        text += "╚══════════════════════════════════════════════════════╝\n"

        return text


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    recommender = StockRecommender()

    # Example data
    technical_data = {
        'moving_averages': {'trend': 'uptrend'},
        'rsi': 55,
        'macd_signal': 'buy',
        'volume_signal': 'strong',
    }

    fundamental_data = {
        'pe_ratio': {'assessment': 'fair', 'score': 70},
        'roe': {'assessment': 'good', 'score': 80},
        'revenue_growth': {'assessment': 'good'},
        'debt_to_equity': {'assessment': 'low'},
    }

    recommendation = recommender.generate_recommendation(
        'AAPL',
        180.50,
        75.0,
        technical_data,
        fundamental_data
    )

    print(recommender.format_recommendation(recommendation)) 
