\# 📊 Stock Analysis Agent



Daily stock market analyzer for Israeli (TASE) and US (NYSE/NASDAQ) markets with technical and fundamental analysis.



\## ✨ Features



\- \*\*Technical Analysis\*\*: RSI, MACD, Moving Averages, Bollinger Bands, Volume Analysis

\- \*\*Fundamental Analysis\*\*: P/E Ratio, ROE, Profit Margins, Debt-to-Equity, Growth Rates

\- \*\*Intelligent Scoring\*\*: Weighted combination (40% technical, 35% fundamental, 25% sentiment)

\- \*\*Daily Automation\*\*: GitHub Actions runs daily at 14:00 (2 PM) Israel time

\- \*\*Telegram Notifications\*\*: Get daily reports directly to your phone

\- \*\*100+ Stocks\*\*: Analyzes both Israeli and US markets



\## 🚀 Quick Start



\### 1. Install Dependencies



```bash

pip install -r requirements.txt

```



\### 2. Configure Environment



Copy `.env.example` to `.env` and add your Telegram credentials:



```bash

cp .env.example .env

```



Edit `.env` with:

\- `TELEGRAM\_BOT\_TOKEN` - Your bot token from @BotFather

\- `TELEGRAM\_CHAT\_ID` - Your chat ID (see SETUP\_GUIDE.md)



\### 3. Run Locally



```bash

python main.py

```



\## 📱 Telegram Setup



1\. Message @BotFather on Telegram

2\. Type `/newbot` and follow instructions

3\. Copy the token and paste in `.env`

4\. Get your Chat ID by messaging @userinfobot

5\. Copy Chat ID and paste in `.env`



\## 🔧 Configuration



Edit `config.yml` to customize:

\- Markets to analyze (Israel/USA)

\- Scoring weights

\- Risk management (stop loss, take profit)

\- Scheduling



\## 📊 Scoring System



| Score | Action | Confidence |

|-------|--------|------------|

| 80-100 | STRONG BUY | 95% |

| 65-79 | BUY | 80% |

| 50-64 | HOLD | 50% |

| 35-49 | SELL | 70% |

| 0-34 | STRONG SELL | 90% |



\## 🤖 GitHub Actions Setup



1\. Push code to GitHub

2\. Go to Settings → Secrets and variables → Actions

3\. Add `TELEGRAM\_BOT\_TOKEN` secret

4\. Add `TELEGRAM\_CHAT\_ID` secret

5\. Workflow runs automatically daily



\## 📈 Output



\- Daily text report saved to `reports/`

\- Telegram message with top recommendations

\- Full analysis table with scores and targets



\## 🐛 Troubleshooting



\*\*No data fetched\*\*: Check internet connection and stock symbols



\*\*Telegram error\*\*: Verify bot token and chat ID in `.env`



\*\*GitHub Actions fails\*\*: Check logs in Actions tab



\## 📚 Documentation



\- See `SETUP\_GUIDE.md` for detailed setup

\- See `QUICKSTART.md` for 5-minute start

\- See `INDEX.md` for complete file reference



\## 📄 License



MIT

