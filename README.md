# stock-analysis-toolkit

A personal GitHub Copilot CLI plugin that downloads historical stock data and
runs a full analysis + SMA-crossover backtest pipeline for any ticker and
date range.

## Quick Start

**Prerequisites:** [GitHub Copilot CLI](https://docs.github.com/copilot/how-tos/use-copilot-agents/use-copilot-cli) and Python 3 with pip.

```bash
# 1. Install the plugin
copilot plugin install senthilkumar-eswaren/stock-analysis-toolkit

# 2. Install Python dependencies
python3 -m pip install yfinance pandas numpy matplotlib seaborn
```

Then just ask Copilot naturally:

> "Analyze RELIANCE on NSE from 2015 to 2025 and backtest a 21/50 SMA crossover strategy"

> "Analyze AAPL from 2018 to 2025"

**Notes:**
- Works for US stocks (NYSE/NASDAQ, `$`) and Indian stocks (NSE/BSE, `Rs`) — use `--exchange NSE`/`--exchange BSE` for plain Indian tickers, or pass an already-suffixed symbol like `RELIANCE.NS`.
- Outputs (CSVs, charts, dashboard PNG) are saved to an `output_<SYMBOL>_<start>_<end>/` folder in your working directory.
- This is a direct GitHub-repo install (not a marketplace), so Copilot may show a deprecation warning — that's expected and harmless.
- To update later: `copilot plugin update stock-analysis-toolkit`

## Example Runs

- [`examples/msft/`](examples/msft/README.md) — US stock (MSFT, NYSE/NASDAQ, `$`), 2009–2025
- [`examples/infy/`](examples/infy/README.md) — Indian stock (INFY, NSE, `Rs`), 2015–2025
- [`examples/ionq/`](examples/ionq/README.md) — US stock (IONQ, NYSE, `$`), 2015–2025 (data from 2021 IPO)

All three include full generated charts, CSVs, and backtest stats produced
directly by the script.

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
> strategy with $2,00,000 capital."

> "Analyze RELIANCE on NSE from 2015 to 2025 and backtest a 21/50 SMA
> crossover strategy with Rs 2,00,000 capital."

Or run the script directly:

```bash
# US stock (NYSE/NASDAQ) — currency $
python3 scripts/stock_analysis_skill.py --symbol MSFT --start 2009 --end 2025

# NSE stock (India) — currency Rs, .NS suffix auto-added
python3 scripts/stock_analysis_skill.py --symbol RELIANCE --exchange NSE --start 2015 --end 2025

# BSE stock (India) — currency Rs, .BO suffix auto-added
python3 scripts/stock_analysis_skill.py --symbol TCS --exchange BSE --start 2015 --end 2025
```

### Flags

| Flag | Default | Description |
|---|---|---|
| `--symbol` | required | Ticker symbol (plain name or already-suffixed, e.g. `RELIANCE.NS`) |
| `--exchange` | AUTO | `US`, `NSE`, or `BSE`. AUTO detects `.NS`/`.BO` suffix, else assumes US |
| `--start` | required | Start year |
| `--end` | required | End year (exclusive) |
| `--recent-years` | 8 | Window for recent stats/heatmap |
| `--capital` | 200000 | Starting backtest capital (in the resolved currency) |
| `--lot-size` | 50 | Units per trade/lot |
| `--sma-fast` / `--sma-slow` | 21 / 50 | Crossover SMA windows |
| `--outdir` | auto | Output directory |

## Dependencies

```bash
python3 -m pip install yfinance pandas numpy matplotlib seaborn
```

## Installation notes

Install via `copilot plugin install senthilkumar-eswaren/stock-analysis-toolkit`
(see Quick Start above). To try local changes before pushing, you can also
install directly from a local path: `copilot plugin install /path/to/stock-analysis-toolkit`.
