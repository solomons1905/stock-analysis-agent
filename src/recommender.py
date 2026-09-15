"""
Recommendation Module
Turns a score into an action with entry price, stop loss and profit target.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class StockRecommender:
    """Generates investment recommendations from the combined score."""

    def __init__(self, stop_loss_percent: float = 3.0,
                 take_profit_percent: float = 15.0):
        self.logger = logging.getLogger(__name__)
        self.stop_loss_percent = float(stop_loss_percent)
        self.take_profit_percent = float(take_profit_percent)

    # ------------------------------------------------------------------ #
    # Recommendation
    # ------------------------------------------------------------------ #

    def generate_recommendation(self, symbol: str, current_price: float,
                                overall_score: float, technical_data: Dict,
                                fundamental_data: Dict,
                                currency: str = "USD") -> Dict:
        """Build the full recommendation for one stock."""
        try:
            current_price = float(current_price)

            if overall_score >= 80:
                action, confidence = "STRONG BUY", 0.95
                stop_pct, target_pct = 2.0, 20.0
            elif overall_score >= 65:
                action, confidence = "BUY", 0.80
                stop_pct, target_pct = self.stop_loss_percent, self.take_profit_percent
            elif overall_score >= 50:
                action, confidence = "HOLD", 0.50
                stop_pct, target_pct = 0.0, 0.0
            elif overall_score >= 35:
                action, confidence = "SELL", 0.70
                stop_pct, target_pct = 0.0, 0.0
            else:
                action, confidence = "STRONG SELL", 0.90
                stop_pct, target_pct = 0.0, 0.0

            entry_price = round(current_price, 2)
            stop_loss = (round(current_price * (1 - stop_pct / 100), 2)
                         if stop_pct > 0 else None)
            target_price = (round(current_price * (1 + target_pct / 100), 2)
                            if target_pct > 0 else None)

            risk_reward_ratio = 0.0
            if stop_loss is not None and target_price is not None:
                risk = entry_price - stop_loss
                reward = target_price - entry_price
                if risk > 0:
                    risk_reward_ratio = round(reward / risk, 2)

            return {
                'symbol': symbol,
                'action': action,
                'confidence': round(confidence, 2),
                'overall_score': overall_score,
                'currency': currency,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target_price': target_price,
                'risk_reward_ratio': risk_reward_ratio,
                'reasons': self._generate_reasons(
                    overall_score, technical_data, fundamental_data),
                'timeframe': 'medium-term (2-6 months)',
            }

        except Exception as exc:  # noqa: BLE001
            self.logger.error("Recommendation failed for %s: %s", symbol, exc)
            return self._default_recommendation(symbol, current_price, currency)

    # ------------------------------------------------------------------ #
    # Reasoning
    # ------------------------------------------------------------------ #

    @staticmethod
    def _generate_reasons(overall_score: float, technical_data: Dict,
                          fundamental_data: Dict) -> List[str]:
        """Explain, in plain language, what drove the recommendation."""
        reasons: List[str] = []

        technical_data = technical_data or {}
        fundamental_data = fundamental_data or {}

        trend = (technical_data.get('moving_averages') or {}).get('trend')
        trend_text = {
            'strong_uptrend': "Strong uptrend confirmed by the 20/50/200 day averages",
            'uptrend': "Uptrend identified by the moving averages",
            'downtrend': "Downtrend identified by the moving averages",
            'strong_downtrend': "Strong downtrend across all moving averages",
        }.get(trend)
        if trend_text:
            reasons.append(trend_text)

        rsi = technical_data.get('rsi')
        if rsi is not None:
            if rsi < 30:
                reasons.append(f"Oversold on RSI ({rsi}) - a rebound is possible")
            elif rsi > 70:
                reasons.append(f"Overbought on RSI ({rsi}) - the move looks stretched")

        macd_signal = technical_data.get('macd_signal')
        if macd_signal == 'buy':
            reasons.append("MACD sits above its signal line (bullish crossover)")
        elif macd_signal == 'sell':
            reasons.append("MACD sits below its signal line (bearish crossover)")

        volume_signal = technical_data.get('volume_signal')
        if volume_signal == 'strong':
            reasons.append("Trading volume is well above its 20-day average")
        elif volume_signal == 'weak':
            reasons.append("Thin volume - the current move lacks conviction")

        pe = (fundamental_data.get('pe_ratio') or {}).get('assessment')
        if pe in ('cheap', 'very_cheap'):
            reasons.append(f"P/E ratio is {pe.replace('_', ' ')} - attractive valuation")
        elif pe in ('expensive', 'very_expensive'):
            reasons.append(f"P/E ratio is {pe.replace('_', ' ')} - valuation risk")
        elif pe == 'loss_making':
            reasons.append("Company is currently loss-making (no positive P/E)")

        roe_score = (fundamental_data.get('roe') or {}).get('score')
        if roe_score is not None and roe_score >= 80:
            reasons.append("Strong return on equity - capital is used efficiently")

        growth = (fundamental_data.get('revenue_growth') or {}).get('assessment')
        if growth in ('excellent', 'very_good', 'good'):
            reasons.append(f"Revenue growth is {growth.replace('_', ' ')}")
        elif growth == 'negative':
            reasons.append("Revenue is shrinking year on year")

        debt = (fundamental_data.get('debt_to_equity') or {}).get('assessment')
        if debt in ('very_low', 'low'):
            reasons.append("Healthy balance sheet with low debt")
        elif debt in ('high', 'very_high'):
            reasons.append("High debt levels - worth monitoring")

        if overall_score >= 80:
            reasons.append("Multiple indicators line up for a strong buy signal")
        elif overall_score < 35:
            reasons.append("Multiple indicators point to weakness or overvaluation")

        return reasons or ["All indicators are neutral"]

    @staticmethod
    def _default_recommendation(symbol: str, current_price: float,
                                currency: str = "USD") -> Dict:
        """Fallback used when the recommendation cannot be computed."""
        return {
            'symbol': symbol,
            'action': 'HOLD',
            'confidence': 0.0,
            'overall_score': 50.0,
            'currency': currency,
            'entry_price': current_price,
            'stop_loss': None,
            'target_price': None,
            'risk_reward_ratio': 0.0,
            'reasons': ["Insufficient data for a reliable analysis"],
            'timeframe': 'N/A',
        }

    # ------------------------------------------------------------------ #
    # Formatting
    # ------------------------------------------------------------------ #

    @staticmethod
    def format_recommendation(recommendation: Dict) -> str:
        """Render a recommendation as a plain-text block for the report."""
        symbol = recommendation.get('symbol', 'N/A')
        action = recommendation.get('action', 'N/A')
        score = recommendation.get('overall_score', 0)
        confidence = recommendation.get('confidence', 0) or 0
        entry = recommendation.get('entry_price') or 0
        stop_loss = recommendation.get('stop_loss')
        target = recommendation.get('target_price')
        ratio = recommendation.get('risk_reward_ratio') or 0
        reasons = recommendation.get('reasons') or []
        currency = recommendation.get('currency') or ''

        lines = [
            "-" * 70,
            f"  {symbol}: {action}",
            "-" * 70,
            f"  Score: {score}/100   |   Confidence: {confidence * 100:.0f}%",
            f"  Entry price: {entry:.2f} {currency}".rstrip(),
        ]

        if stop_loss is not None and entry:
            lines.append(
                f"  Stop loss:   {stop_loss:.2f} ({(stop_loss / entry - 1) * 100:+.1f}%)")
        if target is not None and entry:
            lines.append(
                f"  Target:      {target:.2f} ({(target / entry - 1) * 100:+.1f}%)")
        if ratio > 0:
            lines.append(f"  Risk/reward: {ratio:.2f} : 1")

        lines.append("  Reasons:")
        lines.extend(f"    - {reason}" for reason in reasons)
        lines.append("")

        return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    recommender = StockRecommender()
    rec = recommender.generate_recommendation(
        'AAPL', 180.50, 75.0,
        {'moving_averages': {'trend': 'uptrend'}, 'rsi': 42, 'macd_signal': 'buy',
         'volume_signal': 'strong'},
        {'pe_ratio': {'assessment': 'fair'}, 'roe': {'score': 85.0},
         'revenue_growth': {'assessment': 'good'},
         'debt_to_equity': {'assessment': 'low'}},
    )
    print(recommender.format_recommendation(rec))
