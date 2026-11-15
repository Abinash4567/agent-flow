# Trading Bot Monitoring Dashboard (Level 4)

Real-time monitoring interface for the quantitative & NLP crypto trading bot, built with **React 18**, **TypeScript**, **Tailwind CSS**, and **Recharts**.

## Features

- **Live System Telemetry:** Shows bot daemon operational status, loop health, and Binance Spot Testnet connection mode.
- **Wallet & Balance Overview:** Real-time balances for USDT, BTC, and total estimated portfolio value.
- **Active Position & Risk Tracker:** Displays current open trade size, entry price, live price, and real-time unrealized PnL with Stop-Loss (-2%) and Take-Profit (+6%) guardrails.
- **Interactive Price & EMA Chart:** Visualizes live OHLCV price action alongside EMA 9 (momentum) and EMA 21 (trend) indicators with Recharts.
- **NLP News Sentiment Feed:** Live breaking crypto headlines scored by ProsusAI FinBERT into Positive, Negative, or Neutral postures.

## Quick Start

### 1. Install Dependencies

```bash
npm install
```

### 2. Start Development Server

```bash
npm run dev
# The dashboard runs at http://localhost:5173
```

### 3. Build for Production

```bash
npm run build
```

The frontend connects to the FastAPI backend bridge running at `http://localhost:8000`. You can launch both simultaneously from the monorepo root using `make dev`.
