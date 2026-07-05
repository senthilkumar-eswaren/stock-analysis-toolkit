---
name: stock-analysis
description: >
  Use this skill when the user asks to download or analyze historical stock
  data, run descriptive statistics/trend/volatility/seasonality analysis on a
  ticker, or backtest a moving-average crossover trading strategy. Triggers on
  requests like "analyze AAPL stock", "backtest a SMA crossover strategy for
  TSLA", "download historical data for MSFT and give me a dashboard", or any
  request naming a stock ticker plus a date range for analysis/backtesting.
---

# Stock Analysis Toolkit

Runs a complete stock analysis + SMA crossover backtest pipeline for any
ticker and date range using the bundled `stock_analysis_skill.py` script.

## What it does

1. Downloads historical OHLCV data via `yfinance` for the requested ticker
   and date range.
2. Produces a dataset overview, summary statistics, trend chart, volatility
   chart, 50/200-day moving averages, yearly performance chart, monthly
   returns heatmap, and seasonality chart + a text report.
3. Backtests a configurable fast/slow SMA crossover strategy (default 21/50):
   generates +1 (Buy) / -1 (Sell) / 0 (No signal) signals, opens long/short
   trades on each crossover, and computes P&L per trade using a configurable
   lot size and starting capital.
4. Outputs a full trade log CSV, a stats summary, and a dashboard PNG
   (price+signals, equity curve, drawdown, stats box, win/loss pie).

## How to run it

Invoke the bundled script with the plugin-relative path:

```bash
python3 "${COPILOT_PLUGIN_DIR:-$(dirname "$0")}/../../scripts/stock_analysis_skill.py" \
  --symbol <TICKER> --start <START_YEAR> --end <END_YEAR>
```

In practice, resolve the script's absolute path relative to this SKILL.md
file (it lives at `../../scripts/stock_analysis_skill.py` from this skill
directory) and invoke it with the bash tool. Example:

```bash
python3 ~/copilot-plugins/stock-analysis-toolkit/scripts/stock_analysis_skill.py \
  --symbol MSFT --start 2009 --end 2025
```

### Arguments to collect from the user (ask if not given)

- `--symbol` (required): ticker symbol, e.g. MSFT, AAPL, TSLA
- `--start` (required): start year, e.g. 2009
- `--end` (required): end year (exclusive upper bound), e.g. 2025

### Optional flags (use sensible defaults, only prompt if user wants to customize)

- `--recent-years` (default 8): window used for "recent" stats/heatmap sections
- `--capital` (default 200000): starting capital for the backtest
- `--lot-size` (default 50): units traded per lot/signal
- `--sma-fast` / `--sma-slow` (default 21 / 50): crossover SMA windows
- `--outdir` (default `output_<SYMBOL>_<start>_<end>`): output directory

## Dependencies

Requires `yfinance`, `pandas`, `numpy`, `matplotlib`, and `seaborn`. Install
if missing:

```bash
python3 -m pip install yfinance pandas numpy matplotlib seaborn --quiet
```

## After running

Read back the printed stats block (total trades, win rate, total return,
CAGR, max drawdown) and summarize the dashboard PNG location for the user.
Offer to open/inspect specific output files (trade CSV, dashboard image) on
request.
