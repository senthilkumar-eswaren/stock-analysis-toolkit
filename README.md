# stock-analysis-toolkit

A personal GitHub Copilot CLI plugin that downloads historical stock data and
runs a full analysis + SMA-crossover backtest pipeline for any ticker and
date range.

## What's included

- **Skill**: `stock-analysis` — teaches Copilot when/how to invoke the
  bundled analysis script based on natural-language requests.
- **Script**: `scripts/stock_analysis_skill.py` — the actual pipeline:
  1. Downloads OHLCV data via `yfinance`
  2. Descriptive analysis: trend, volatility, moving averages, yearly
     performance, monthly returns heatmap, seasonality
  3. 21/50 SMA crossover backtest: Buy(+1)/Sell(-1)/No-signal(0), long &
     short trades, P&L, equity curve, drawdown
  4. Full dashboard PNG + CSV trade log + stats file

## Usage

Just ask Copilot naturally, e.g.:

> "Analyze AAPL from 2015 to 2025 and backtest a 21/50 SMA crossover
> strategy with Rs 2,00,000 capital."

Or run the script directly:

```bash
python3 scripts/stock_analysis_skill.py --symbol MSFT --start 2009 --end 2025
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--symbol` | required | Ticker symbol |
| `--start` | required | Start year |
| `--end` | required | End year (exclusive) |
| `--recent-years` | 8 | Window for recent stats/heatmap |
| `--capital` | 200000 | Starting backtest capital |
| `--lot-size` | 50 | Units per trade/lot |
| `--sma-fast` / `--sma-slow` | 21 / 50 | Crossover SMA windows |
| `--outdir` | auto | Output directory |

## Dependencies

```bash
python3 -m pip install yfinance pandas numpy matplotlib seaborn
```

## Installation (local/personal use)

This plugin lives at `~/copilot-plugins/stock-analysis-toolkit` and is
installed for personal use only (not published to a marketplace). See the
main Copilot CLI docs for how local plugins are loaded, or symlink/copy this
directory into `~/.copilot/installed-plugins/` and enable it in
`~/.copilot/settings.json`.
