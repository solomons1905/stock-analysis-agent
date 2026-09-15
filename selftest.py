"""
Offline self-test.

Runs every analysis stage against synthetic price data so the pipeline can be
verified without touching the network. Exits non-zero if anything breaks.
"""

import logging
import sys

import numpy as np
import pandas as pd

from src.fundamental_analyzer import FundamentalAnalyzer
from src.recommender import StockRecommender
from src.scorer import StockScorer
from src.technical_analyzer import TechnicalAnalyzer
from src.telegram_notifier import TelegramNotifier

logging.basicConfig(level=logging.WARNING)

failures = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label} {detail}")
        failures.append(label)


def make_history(days: int = 400, trend: float = 0.0,
                 seed: int = 7, noise: float = 0.012) -> pd.DataFrame:
    """
    Build a synthetic OHLCV frame shaped like yfinance output.

    ``noise`` is the daily standard deviation. Trend tests pass a small value
    so the drift dominates the random walk; without that the path can easily
    finish in the opposite direction over 400 days.
    """
    rng = np.random.default_rng(seed)
    returns = rng.normal(trend, noise, days)
    close = 100 * np.exp(np.cumsum(returns))

    return pd.DataFrame({
        'open': close * rng.uniform(0.99, 1.01, days),
        'high': close * rng.uniform(1.00, 1.03, days),
        'low': close * rng.uniform(0.97, 1.00, days),
        'close': close,
        'volume': rng.integers(1_000_000, 9_000_000, days),
    }, index=pd.date_range('2024-01-01', periods=days, freq='B'))


print("\n1. Technical analysis")
ta = TechnicalAnalyzer()
up = ta.analyze(make_history(400, trend=0.0025, noise=0.004), 'UPTREND')
down = ta.analyze(make_history(400, trend=-0.0025, noise=0.004, seed=11),
                  'DOWNTREND')

check("returns all indicators",
      set(up) >= {'moving_averages', 'rsi', 'macd', 'bollinger_bands', 'volume'})
check("RSI within 0-100", up['rsi'] is not None and 0 <= up['rsi'] <= 100,
      f"(got {up['rsi']})")
check("MA200 computed on 400 days", up['moving_averages']['ma200'] is not None)
check("rising series reads bullish",
      up['moving_averages']['trend'] in ('uptrend', 'strong_uptrend'),
      f"(got {up['moving_averages']['trend']})")
check("falling series reads bearish",
      down['moving_averages']['trend'] in ('downtrend', 'strong_downtrend'),
      f"(got {down['moving_averages']['trend']})")

short = ta.analyze(make_history(60), 'SHORT')
check("short history degrades instead of crashing",
      bool(short) and short['moving_averages']['ma200'] is None)
check("30 days of data is rejected cleanly", ta.analyze(make_history(20)) == {})

print("\n2. Fundamental analysis")
fa = FundamentalAnalyzer()

full = fa.analyze({
    'symbol': 'TEST', 'pe_ratio': 18.0, 'roe': 0.28, 'profit_margin': 0.22,
    'debt_to_equity': 145.0,          # yfinance percent form -> 1.45x
    'revenue_growth': 0.18, 'earnings_growth': 0.25, 'dividend_yield': 0.021,
})
check("debt/equity percent form rescaled",
      full['debt_to_equity']['assessment'] == 'moderate',
      f"(got {full['debt_to_equity']['assessment']})")
check("strong fundamentals score high", full['overall_score'] > 70,
      f"(got {full['overall_score']})")

sparse = fa.analyze({'symbol': 'SPARSE', 'pe_ratio': 12.0, 'roe': 0.30})
check("missing metrics excluded from average",
      sparse['metrics_available'] == 2 and sparse['overall_score'] > 80,
      f"(n={sparse['metrics_available']}, score={sparse['overall_score']})")

empty = fa.analyze({'symbol': 'EMPTY'})
check("no data falls back to neutral", empty['overall_score'] == 50.0)
check("loss-making P/E handled",
      fa.analyze_pe_ratio(-5.0)[0] == 'loss_making')

# Regression: real AAPL figures pulled from yfinance on 2026-09-15.
# ROE arrives as 1.4875, meaning 148.75%. A magnitude-based guess read that
# as 1.49% and graded one of the best returns in the S&P 500 as "weak".
check("ROE above 100% graded as excellent",
      fa.analyze_roe(1.4875) == ('excellent', 95.0),
      f"(got {fa.analyze_roe(1.4875)})")
check("ordinary ROE still correct",
      fa.analyze_roe(0.18) == ('good', 75.0), f"(got {fa.analyze_roe(0.18)})")
check("negative ROE graded as poor", fa.analyze_roe(-0.05)[0] == 'poor')
check("growth above 100% graded as excellent",
      fa.analyze_revenue_growth(1.5) == ('excellent', 95.0),
      f"(got {fa.analyze_revenue_growth(1.5)})")
check("margin above 100% does not wrap around",
      fa.analyze_profit_margin(1.2)[0] == 'excellent')

from src.data_fetcher import DataFetcher  # noqa: E402

aapl_info = {'dividendRate': 1.06, 'currentPrice': 330.03,
             'trailingAnnualDividendYield': 0.0032}
yield_pct = DataFetcher._dividend_yield_percent(aapl_info)
check("dividend yield derived from rate and price",
      yield_pct is not None and 0.30 < yield_pct < 0.35,
      f"(got {yield_pct})")
check("a 0.32% yield is graded low, not suspiciously high",
      fa.analyze_dividend_yield(yield_pct)[0] == 'low',
      f"(got {fa.analyze_dividend_yield(yield_pct)})")
check("falls back to the trailing fraction when rate is missing",
      abs(DataFetcher._dividend_yield_percent(
          {'trailingAnnualDividendYield': 0.042}) - 4.2) < 1e-9)
check("a real 4% yield is graded good",
      fa.analyze_dividend_yield(4.2)[0] == 'good')
check("no dividend data returns None",
      DataFetcher._dividend_yield_percent({}) is None)

print("\n3. Scoring")
check("config.yml key style accepted (the old KeyError)",
      StockScorer({'technical_weight': 0.5, 'fundamental_weight': 0.3,
                   'sentiment_weight': 0.2}).weights['technical'] == 0.5)
check("short key style accepted",
      StockScorer({'technical': 0.5, 'fundamental': 0.3,
                   'sentiment': 0.2}).weights['technical'] == 0.5)
check("unnormalised weights normalised",
      abs(sum(StockScorer({'technical_weight': 2, 'fundamental_weight': 1,
                           'sentiment_weight': 1}).weights.values()) - 1.0) < 1e-6)
check("class defaults never mutated",
      StockScorer.DEFAULT_WEIGHTS['technical'] == 0.40)
check("empty config uses defaults", StockScorer({}).weights['technical'] == 0.40)

scorer = StockScorer({'technical_weight': 0.40, 'fundamental_weight': 0.35,
                      'sentiment_weight': 0.25})
good = scorer.score(up, full)
bad = scorer.score(down, fa.analyze({
    'symbol': 'BAD', 'pe_ratio': 60.0, 'roe': -0.1, 'profit_margin': -0.05,
    'debt_to_equity': 380.0, 'revenue_growth': -0.2, 'earnings_growth': -0.3,
}))
check("scores stay inside 0-100", 0 <= good['overall_score'] <= 100)
check("good company outscores bad one",
      good['overall_score'] > bad['overall_score'],
      f"({good['overall_score']} vs {bad['overall_score']})")
check("empty input is neutral", scorer.score({}, {})['overall_score'] == 50.0)

print("\n4. Recommendations")
rec = StockRecommender(stop_loss_percent=3.0, take_profit_percent=15.0)

buy = rec.generate_recommendation('TEST', 100.0, 70.0, up, full)
check("BUY sets a 3% stop", buy['stop_loss'] == 97.0, f"(got {buy['stop_loss']})")
check("BUY sets a 15% target", buy['target_price'] == 115.0,
      f"(got {buy['target_price']})")
check("risk/reward is 5:1", buy['risk_reward_ratio'] == 5.0,
      f"(got {buy['risk_reward_ratio']})")

strong = rec.generate_recommendation('TEST', 100.0, 85.0, up, full)
check("STRONG BUY tightens the stop to 2%", strong['stop_loss'] == 98.0)
check("STRONG BUY targets 20%", strong['target_price'] == 120.0)

hold = rec.generate_recommendation('TEST', 100.0, 55.0, up, full)
check("HOLD has no stop or target",
      hold['stop_loss'] is None and hold['target_price'] is None)
check("reasons are generated", len(buy['reasons']) >= 3,
      f"(got {len(buy['reasons'])})")
check("formatting a HOLD (None prices) does not crash",
      'HOLD' in rec.format_recommendation(hold))

print("\n5. Telegram message building")
results = []
for i in range(60):
    score = 90 - i
    r = rec.generate_recommendation(f'SYM{i}', 100.0 + i, score, up, full)
    results.append({'symbol': f'SYM{i}', 'current_price': 100.0 + i,
                    'scores': {'overall_score': score}, 'recommendation': r})

notifier = TelegramNotifier(bot_token='x', chat_id='y')
message = notifier.format_recommendations_message(results)
chunks = notifier._split_message(message)

check("message built for 60 stocks", len(message) > 100)
check("every chunk respects the 4096 cap",
      all(len(c) <= 4096 for c in chunks),
      f"(max {max(len(c) for c in chunks)})")
check("HOLD entries with no target do not crash",
      bool(notifier.format_recommendations_message([{
          'symbol': 'H', 'current_price': 10.0,
          'scores': {'overall_score': 55.0},
          'recommendation': hold}])))
check("empty result set handled",
      'No results' in notifier.format_recommendations_message([]))
check("unconfigured notifier reports itself",
      TelegramNotifier(bot_token='', chat_id='').is_configured() is False)

print("\n6. Report writing")
import main as agent_main  # noqa: E402

agent = agent_main.StockAnalysisAgent('config.yml')
for r in results:
    r.setdefault('market', 'us')
path = agent.generate_report(results, report_dir='reports')
check("report file created", bool(path))

with open(path, encoding='utf-8') as fh:
    body = fh.read()
check("report lists every stock", body.count('SYM') >= 60)
check("report has a summary", 'SUMMARY' in body)
check("report carries a disclaimer", 'not investment advice' in body)
check("empty results still produce a report",
      bool(agent.generate_report([], report_dir='reports')))

print("\n" + "=" * 50)
if failures:
    print(f"{len(failures)} CHECK(S) FAILED: {', '.join(failures)}")
    sys.exit(1)

print("ALL CHECKS PASSED")
sys.exit(0)
