# Stock Analysis Agent

Daily analysis of the Israeli (TASE) and US (NYSE / NASDAQ) markets. Scores
every stock on technical and fundamental grounds, writes a report and sends the
summary to Telegram. Runs itself on GitHub Actions, free of charge.

סוכן לניתוח יומי של שוק ההון הישראלי והאמריקאי. רץ אוטומטית ב-GitHub Actions
כל יום בשעה 14:00 ושולח דוח לטלגרם.

## What it does

Each run downloads a year of price history and the current fundamentals for
roughly 120 stocks, then produces a score out of 100 for each one:

| Dimension   | Weight | What goes into it                                  |
|-------------|--------|----------------------------------------------------|
| Technical   | 40%    | 20/50/200-day averages, RSI, MACD, Bollinger, volume |
| Fundamental | 35%    | P/E, ROE, margin, debt/equity, growth, dividend      |
| Sentiment   | 25%    | Reserved for news analysis; currently neutral        |

The score maps onto an action:

| Score  | Action      | Confidence | Stop loss | Target |
|--------|-------------|------------|-----------|--------|
| 80-100 | STRONG BUY  | 95%        | -2%       | +20%   |
| 65-79  | BUY         | 80%        | -3%       | +15%   |
| 50-64  | HOLD        | 50%        | -         | -      |
| 35-49  | SELL        | 70%        | -         | -      |
| 0-34   | STRONG SELL | 90%        | -         | -      |

## Setup

### 1. Create the Telegram bot

Message **@BotFather** in Telegram, send `/newbot`, follow the prompts and copy
the token it gives you. It looks like `123456789:AAEhBOweik6ad...`.

### 2. Add the token to GitHub

In your repository go to **Settings -> Secrets and variables -> Actions**, press
**New repository secret** and add:

- `TELEGRAM_BOT_TOKEN` - the token from BotFather

### 3. Find your chat id

Open your new bot in Telegram and press **Start** (or send it any message).
Then, in the **Actions** tab, run the **Find Telegram Chat ID** workflow. Your
chat id is printed in the log of the *Look up chat id* step.

Add it as a second secret:

- `TELEGRAM_CHAT_ID` - the number from the log

The bot cannot message you until you have written to it first — that is a
Telegram rule, not a bug.

### 4. Run it

In the **Actions** tab, run **Daily Stock Analysis** manually to check
everything works. After that it runs on its own every weekday.

## Schedule

The cron line in `.github/workflows/daily_analysis.yml` is `0 11 * * 1-5`:
11:00 UTC, Monday to Friday, which is 14:00 in Israel during winter time and
13:00 during summer time. To change the hour, edit that line — GitHub Actions
always works in UTC.

## Running it locally

Needs Python 3.10 or newer.

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your token and chat id in .env
python main.py
```

Useful flags while testing:

```bash
python main.py --limit 5              # only the first 5 stocks per market
python main.py --market us            # skip the Israeli list
python selftest.py                    # offline check, no network needed
```

## Configuration

`config.yml` controls the weights and the risk settings:

```yaml
scoring:
  technical_weight: 0.40
  fundamental_weight: 0.35
  sentiment_weight: 0.25

risk:
  default_stop_loss_percent: 3.0
  default_take_profit_percent: 15.0
```

The stock lists live at the top of `src/data_fetcher.py`. Israeli symbols use
the Yahoo Finance `.TA` suffix, for example `POLI.TA` for Bank Hapoalim.

## Project layout

```
main.py                     orchestrates a run
get_chat_id.py              helper for finding your Telegram chat id
selftest.py                 offline test of the whole pipeline
config.yml                  weights, risk settings
src/data_fetcher.py         downloads prices and fundamentals
src/technical_analyzer.py   RSI, MACD, moving averages, Bollinger, volume
src/fundamental_analyzer.py P/E, ROE, margins, debt, growth
src/scorer.py               blends the three dimensions into one score
src/recommender.py          action, entry, stop loss, target, reasoning
src/telegram_notifier.py    Telegram Bot API client
```

## Troubleshooting

**No Telegram message.** Check the workflow log. If it says the token was
rejected, re-copy it from BotFather. If it says "chat not found", you have not
sent your bot a message yet, or the chat id is wrong — rerun the *Find Telegram
Chat ID* workflow.

**A stock is skipped.** Yahoo Finance has no data for that symbol, or it has
been delisted. The run continues; check `stock_agent.log` in the workflow
artifacts for the details.

**The workflow fails immediately.** GitHub retires old action versions.
If you see a deprecation error, bump the `uses:` version numbers in
`.github/workflows/daily_analysis.yml`.

## Disclaimer

This is an automated screening tool built for personal use. It is not
investment advice, the scores are not a prediction, and nobody should buy or
sell anything on the strength of them alone. Do your own research.

הכלי נועד לסינון ראשוני בלבד ואינו מהווה ייעוץ השקעות.
