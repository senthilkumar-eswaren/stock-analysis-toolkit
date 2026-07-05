#!/usr/bin/env python3
"""
stock_analysis_skill.py
========================
A reusable "skill" that takes a Stock Symbol + start year + end year and
runs the full analysis pipeline built earlier for MSFT, generalized to
any ticker:

  1. Download historical data (yfinance) for the given date range.
  2. Dataset overview + summary statistics.
  3. Trend, volatility, moving-average, yearly comparison, monthly
     returns heatmap, and seasonality analysis.
  4. 21/50 SMA crossover strategy backtest (long & short trades) with a
     configurable starting capital and lot size.
  5. A full dashboard PNG + all supporting CSVs/PNGs.

Usage
-----
    python3 stock_analysis_skill.py --symbol MSFT --start 2009 --end 2025

Optional flags
---------------
    --recent-years   INT    Window (years) used for "recent" stats/heatmap
                             sections (default: 8)
    --capital        FLOAT  Starting capital for backtest (default: 200000)
    --lot-size       INT    Units per trade / lot (default: 50)
    --sma-fast       INT    Fast SMA window (default: 21)
    --sma-slow       INT    Slow SMA window (default: 50)
    --outdir         STR    Output directory (default: output_<SYMBOL>_<start>_<end>)

All outputs (CSVs + PNG charts + dashboard) are written to --outdir.
"""

import argparse
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import yfinance as yf

MONTH_ORDER = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ----------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Full stock analysis + SMA crossover backtest skill.")
    p.add_argument("--symbol", required=True,
                    help="Ticker symbol. US: MSFT, AAPL, TSLA. NSE: RELIANCE, TCS, INFY. "
                         "BSE: 500325 or RELIANCE. Exchange suffix (.NS/.BO) is auto-added "
                         "if --exchange is NSE/BSE and not already present.")
    p.add_argument("--exchange", default="AUTO", choices=["AUTO", "US", "NSE", "BSE"],
                    help="Exchange: US (NYSE/NASDAQ, default), NSE, or BSE (India). "
                         "AUTO detects from symbol suffix (.NS/.BO) or a raw NSE-listed name; "
                         "falls back to US. Determines currency ($ for US, Rs for NSE/BSE).")
    p.add_argument("--start", required=True, type=int, help="Start year, e.g. 2009")
    p.add_argument("--end", required=True, type=int, help="End year (exclusive upper bound), e.g. 2025")
    p.add_argument("--recent-years", type=int, default=8, help="Recent-years window for stats/heatmap (default 8)")
    p.add_argument("--capital", type=float, default=200000, help="Starting capital for backtest (default 200000)")
    p.add_argument("--lot-size", type=int, default=50, help="Units per lot/trade (default 50)")
    p.add_argument("--sma-fast", type=int, default=21, help="Fast SMA window (default 21)")
    p.add_argument("--sma-slow", type=int, default=50, help="Slow SMA window (default 50)")
    p.add_argument("--outdir", default=None, help="Output directory (default auto-generated)")
    return p.parse_args()


# ----------------------------------------------------------------------
# Exchange / currency resolution
# ----------------------------------------------------------------------
# yfinance suffix convention: NSE tickers end in ".NS", BSE tickers end in ".BO".
# Currency is USD for US-listed symbols and INR for NSE/BSE-listed symbols.
CURRENCY_BY_EXCHANGE = {"US": "$", "NSE": "Rs", "BSE": "Rs"}


def resolve_symbol_and_currency(symbol, exchange):
    """Normalize the ticker with the right yfinance suffix and pick the currency symbol."""
    raw = symbol.upper().strip()

    if exchange == "AUTO":
        if raw.endswith(".NS"):
            exchange = "NSE"
        elif raw.endswith(".BO"):
            exchange = "BSE"
        else:
            exchange = "US"

    if exchange == "NSE" and not raw.endswith(".NS"):
        raw = f"{raw}.NS"
    elif exchange == "BSE" and not raw.endswith(".BO"):
        raw = f"{raw}.BO"

    currency = CURRENCY_BY_EXCHANGE[exchange]
    return raw, exchange, currency


# ----------------------------------------------------------------------
# 1. Download
# ----------------------------------------------------------------------
def download_data(symbol, start_year, end_year, outdir):
    end_date = datetime(end_year, 1, 1)
    start_date = end_date - timedelta(days=(end_year - start_year) * 365)
    start_str, end_str = start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    print(f"[1/4] Downloading {symbol} data from {start_str} to {end_str} ...")
    data = yf.download(symbol, start=start_str, end=end_str)
    if data.empty:
        raise ValueError(
            f"No data returned for symbol '{symbol}'. Check the ticker and date range "
            f"(NSE symbols need a '.NS' suffix, BSE symbols need '.BO', e.g. RELIANCE.NS)."
        )

    # yfinance MultiIndex columns -> flatten
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Sanitize symbol for use in filenames (strip dots from .NS/.BO suffixes)
    safe_symbol = symbol.replace(".", "_")
    csv_path = os.path.join(outdir, f"{safe_symbol}_{start_year}_{end_year}.csv")
    data.to_csv(csv_path)
    print(f"      Saved raw data -> {csv_path}")
    return data


# ----------------------------------------------------------------------
# 2. Dataset overview + descriptive analysis
# ----------------------------------------------------------------------
def run_descriptive_analysis(df, symbol, recent_years, outdir, currency="$"):
    print(f"[2/4] Running descriptive analysis (trend, volatility, MAs, seasonality)...")
    safe_symbol = symbol.replace(".", "_")
    df = df.copy()
    df["Daily Return"] = df["Close"].pct_change()

    end_date = df.index.max()
    start_recent = end_date - timedelta(days=recent_years * 365)
    df_recent = df.loc[df.index >= start_recent]

    report_lines = []
    report_lines.append(f"DATASET OVERVIEW - {symbol}")
    report_lines.append(f"Date Range : {df.index.min().date()} to {df.index.max().date()}")
    report_lines.append(f"Total Rows : {len(df)} trading days")
    report_lines.append(f"Currency   : {currency}")
    report_lines.append(f"Features   : {list(df.columns[:5])} (+ derived Daily Return)\n")

    report_lines.append(f"SUMMARY STATISTICS - LAST {recent_years} YEARS")
    report_lines.append(df_recent[["Open", "High", "Low", "Close", "Volume"]].describe().to_string())
    report_lines.append("")

    # Trend chart
    plt.figure(figsize=(12, 6))
    plt.plot(df_recent.index, df_recent["Close"], color="steelblue", linewidth=1.2)
    plt.title(f"{symbol} Closing Price Trend (Last {recent_years} Years)")
    plt.xlabel("Date"); plt.ylabel(f"Close Price ({currency})")
    plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{safe_symbol}_trend.png"), dpi=150); plt.close()

    # Volatility
    df["Volatility_30d"] = df["Daily Return"].rolling(30).std() * np.sqrt(252)
    overall_vol = df["Daily Return"].std() * np.sqrt(252)
    recent_vol = df_recent["Daily Return"].std() * np.sqrt(252)
    report_lines.append("VOLATILITY ANALYSIS")
    report_lines.append(f"Annualized Volatility (full period): {overall_vol:.2%}")
    report_lines.append(f"Annualized Volatility (last {recent_years}y): {recent_vol:.2%}\n")

    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["Volatility_30d"], color="crimson", linewidth=1)
    plt.title(f"{symbol} 30-Day Rolling Annualized Volatility")
    plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{safe_symbol}_volatility.png"), dpi=150); plt.close()

    # Moving averages (50/200 for descriptive section)
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df["Close"], label="Close", alpha=0.5, linewidth=0.8)
    plt.plot(df.index, df["MA50"], label="50-Day MA", color="orange")
    plt.plot(df.index, df["MA200"], label="200-Day MA", color="green")
    plt.title(f"{symbol} Price with 50/200-Day Moving Averages")
    plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{safe_symbol}_moving_averages.png"), dpi=150); plt.close()

    # Yearly performance
    yearly = df["Close"].resample("YE").agg(["first", "last"])
    yearly["Return %"] = (yearly["last"] / yearly["first"] - 1) * 100
    report_lines.append("YEARLY PERFORMANCE")
    report_lines.append(yearly[["Return %"]].round(2).to_string())
    report_lines.append("")

    plt.figure(figsize=(12, 6))
    colors = ["green" if x >= 0 else "red" for x in yearly["Return %"]]
    plt.bar(yearly.index.year, yearly["Return %"], color=colors)
    plt.title(f"{symbol} Yearly Returns (%)")
    plt.grid(alpha=0.3, axis="y"); plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{safe_symbol}_yearly_returns.png"), dpi=150); plt.close()

    # Monthly returns heatmap (recent years)
    monthly_close = df_recent["Close"].resample("ME").last()
    monthly_returns = monthly_close.pct_change() * 100
    monthly_df = monthly_returns.to_frame("Return")
    monthly_df["Year"] = monthly_df.index.year
    monthly_df["Month"] = monthly_df.index.strftime("%b")
    pivot = monthly_df.pivot(index="Year", columns="Month", values="Return").reindex(columns=MONTH_ORDER)

    plt.figure(figsize=(12, 6))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap="RdYlGn", center=0,
                linewidths=0.5, cbar_kws={"label": "Monthly Return (%)"})
    plt.title(f"{symbol} Monthly % Returns Heatmap (Last {recent_years} Years)")
    plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{safe_symbol}_monthly_returns_heatmap.png"), dpi=150); plt.close()

    # Seasonality
    df["Month"] = df.index.strftime("%b")
    seasonal_avg = df.groupby("Month")["Daily Return"].mean().reindex(MONTH_ORDER) * 100
    report_lines.append("SEASONAL PATTERN (avg daily return % by month, full period)")
    report_lines.append(seasonal_avg.round(4).to_string())
    report_lines.append("")

    plt.figure(figsize=(12, 6))
    colors = ["green" if x >= 0 else "red" for x in seasonal_avg]
    plt.bar(seasonal_avg.index, seasonal_avg.values, color=colors)
    plt.title(f"{symbol} Average Daily Return by Month")
    plt.grid(alpha=0.3, axis="y"); plt.tight_layout()
    plt.savefig(os.path.join(outdir, f"{safe_symbol}_seasonality.png"), dpi=150); plt.close()

    report_path = os.path.join(outdir, f"{safe_symbol}_analysis_report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(str(x) for x in report_lines))
    print(f"      Saved analysis charts + report -> {outdir}/")
    return df


# ----------------------------------------------------------------------
# 3 & 4. SMA crossover backtest + dashboard
# ----------------------------------------------------------------------
def run_backtest(df, symbol, recent_years, capital, lot_size, sma_fast, sma_slow, outdir, currency="$"):
    print(f"[3/4] Running {sma_fast}/{sma_slow} SMA crossover backtest "
          f"(last {recent_years}y, capital {currency}{capital:,.0f}, lot size {lot_size})...")
    safe_symbol = symbol.replace(".", "_")
    pnl_col = f"P&L ({currency})"
    cum_col = f"Cumulative P&L ({currency})"
    equity_col = f"Equity ({currency})"

    end_date = df.index.max()
    start_recent = end_date - timedelta(days=recent_years * 365)
    bt = df.loc[df.index >= start_recent].copy()

    bt[f"SMA{sma_fast}"] = bt["Close"].rolling(sma_fast).mean()
    bt[f"SMA{sma_slow}"] = bt["Close"].rolling(sma_slow).mean()
    bt["Prev_Fast"] = bt[f"SMA{sma_fast}"].shift(1)
    bt["Prev_Slow"] = bt[f"SMA{sma_slow}"].shift(1)

    bt["Signal"] = 0
    buy_mask = (bt["Prev_Fast"] <= bt["Prev_Slow"]) & (bt[f"SMA{sma_fast}"] > bt[f"SMA{sma_slow}"])
    sell_mask = (bt["Prev_Fast"] >= bt["Prev_Slow"]) & (bt[f"SMA{sma_fast}"] < bt[f"SMA{sma_slow}"])
    bt.loc[buy_mask, "Signal"] = 1
    bt.loc[sell_mask, "Signal"] = -1

    signals_csv = os.path.join(outdir, f"{safe_symbol}_sma_signals.csv")
    bt.to_csv(signals_csv)

    signals = bt[bt["Signal"] != 0]
    trades = []
    position = entry_price = entry_date = None

    for date, row in signals.iterrows():
        sig, price = row["Signal"], row["Close"]
        if position is None:
            position, entry_price, entry_date = ("LONG" if sig == 1 else "SHORT"), price, date
            continue
        if (position == "LONG" and sig == -1) or (position == "SHORT" and sig == 1):
            exit_price, exit_date = price, date
            pnl_points = (exit_price - entry_price) if position == "LONG" else (entry_price - exit_price)
            trades.append({
                "Entry Date": entry_date, "Exit Date": exit_date, "Direction": position,
                "Entry Price": round(entry_price, 2), "Exit Price": round(exit_price, 2),
                "Points": round(pnl_points, 2), pnl_col: round(pnl_points * lot_size, 2),
            })
            position, entry_price, entry_date = ("LONG" if sig == 1 else "SHORT"), exit_price, exit_date

    if position is not None:
        exit_price, exit_date = bt["Close"].iloc[-1], bt.index[-1]
        pnl_points = (exit_price - entry_price) if position == "LONG" else (entry_price - exit_price)
        trades.append({
            "Entry Date": entry_date, "Exit Date": exit_date, "Direction": position,
            "Entry Price": round(entry_price, 2), "Exit Price": round(exit_price, 2),
            "Points": round(pnl_points, 2), pnl_col: round(pnl_points * lot_size, 2),
        })

    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("      No trades generated in this period.")
        return

    trades_df[cum_col] = trades_df[pnl_col].cumsum()
    trades_df[equity_col] = capital + trades_df[cum_col]
    trades_df["Trade Return %"] = (trades_df[pnl_col] / capital) * 100
    trades_csv = os.path.join(outdir, f"{safe_symbol}_backtest_trades.csv")
    trades_df.to_csv(trades_csv, index=False)

    total_trades = len(trades_df)
    profitable = (trades_df[pnl_col] > 0).sum()
    losses = (trades_df[pnl_col] <= 0).sum()
    win_rate = profitable / total_trades * 100
    final_equity = trades_df[equity_col].iloc[-1]
    total_pnl = final_equity - capital
    total_return_pct = (final_equity / capital - 1) * 100
    years = (bt.index.max() - bt.index.min()).days / 365.25
    cagr = ((final_equity / capital) ** (1 / years) - 1) * 100 if years > 0 else np.nan
    avg_win = trades_df.loc[trades_df[pnl_col] > 0, pnl_col].mean()
    avg_loss = trades_df.loc[trades_df[pnl_col] <= 0, pnl_col].mean()
    best_trade = trades_df[pnl_col].max()
    worst_trade = trades_df[pnl_col].min()
    equity_series = trades_df[equity_col]
    drawdown = (equity_series - equity_series.cummax()) / equity_series.cummax() * 100
    max_dd = drawdown.min()

    stats = {
        "Starting Capital": capital, "Final Equity": final_equity, "Total P&L": total_pnl,
        "Total Return %": total_return_pct, "CAGR %": cagr, "Total Trades": total_trades,
        "Profitable Trades": profitable, "Loss Trades": losses, "Win Rate %": win_rate,
        "Avg Win": avg_win, "Avg Loss": avg_loss, "Best Trade": best_trade,
        "Worst Trade": worst_trade, "Max Drawdown %": max_dd,
    }
    stats_path = os.path.join(outdir, f"{safe_symbol}_backtest_stats.txt")
    with open(stats_path, "w") as f:
        for k, v in stats.items():
            f.write(f"{k}: {v:,.2f}\n")

    print(f"      Saved trades -> {trades_csv}")
    print(f"      Saved stats  -> {stats_path}")
    for k, v in stats.items():
        print(f"        {k}: {v:,.2f}")

    # -------------------- Dashboard --------------------
    print(f"[4/4] Building dashboard...")
    fig = plt.figure(figsize=(16, 14))
    gs = gridspec.GridSpec(4, 2, height_ratios=[2, 1.5, 1, 1.3])

    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(bt.index, bt["Close"], label="Close", color="black", linewidth=0.8, alpha=0.7)
    ax1.plot(bt.index, bt[f"SMA{sma_fast}"], label=f"SMA {sma_fast}", color="orange", linewidth=1)
    ax1.plot(bt.index, bt[f"SMA{sma_slow}"], label=f"SMA {sma_slow}", color="blue", linewidth=1)
    buys, sells = bt[bt["Signal"] == 1], bt[bt["Signal"] == -1]
    ax1.scatter(buys.index, buys["Close"], marker="^", color="green", s=80, label="Buy", zorder=5)
    ax1.scatter(sells.index, sells["Close"], marker="v", color="red", s=80, label="Sell", zorder=5)
    ax1.set_title(f"{symbol} Price with {sma_fast}/{sma_slow} SMA Crossover Signals")
    ax1.legend(loc="upper left", fontsize=8); ax1.grid(alpha=0.3)

    ax2 = fig.add_subplot(gs[1, :])
    equity_plot = pd.concat([pd.Series([capital], index=[bt.index.min()]),
                              trades_df.set_index("Exit Date")[equity_col]])
    ax2.plot(equity_plot.index, equity_plot.values, color="darkgreen", linewidth=1.5, marker="o", markersize=3)
    ax2.axhline(capital, color="gray", linestyle="--", linewidth=1, label="Starting Capital")
    ax2.set_title("Equity Curve"); ax2.legend(fontsize=8); ax2.grid(alpha=0.3)

    ax3 = fig.add_subplot(gs[2, :])
    dd_plot = pd.Series(drawdown.values, index=trades_df["Exit Date"])
    ax3.fill_between(dd_plot.index, dd_plot.values, 0, color="red", alpha=0.4)
    ax3.set_title("Drawdown (%)"); ax3.grid(alpha=0.3)

    ax4 = fig.add_subplot(gs[3, 0]); ax4.axis("off")
    stats_text = (
        f"Starting Capital: {currency}{capital:,.0f}\nFinal Equity: {currency}{final_equity:,.0f}\n"
        f"Total P&L: {currency}{total_pnl:,.0f}\nTotal Return: {total_return_pct:.2f}%\n"
        f"CAGR: {cagr:.2f}%\nTotal Trades: {total_trades}\n"
        f"Profitable Trades: {profitable}\nLoss Trades: {losses}\nWin Rate: {win_rate:.1f}%\n"
        f"Avg Win: {currency}{avg_win:,.0f}   Avg Loss: {currency}{avg_loss:,.0f}\n"
        f"Best Trade: {currency}{best_trade:,.0f}   Worst Trade: {currency}{worst_trade:,.0f}\n"
        f"Max Drawdown: {max_dd:.2f}%"
    )
    ax4.text(0, 1, stats_text, fontsize=10, va="top", family="monospace",
              bbox=dict(boxstyle="round", facecolor="lightyellow"))
    ax4.set_title("Strategy Stats", loc="left")

    ax5 = fig.add_subplot(gs[3, 1])
    ax5.pie([profitable, losses], labels=["Profitable", "Loss"], autopct="%1.1f%%",
            colors=["green", "red"], startangle=90)
    ax5.set_title("Win/Loss Ratio")

    plt.tight_layout()
    dashboard_path = os.path.join(outdir, f"{safe_symbol}_strategy_dashboard.png")
    plt.savefig(dashboard_path, dpi=150); plt.close()
    print(f"      Saved dashboard -> {dashboard_path}")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    args = parse_args()
    symbol, exchange, currency = resolve_symbol_and_currency(args.symbol, args.exchange)
    safe_symbol = symbol.replace(".", "_")
    outdir = args.outdir or f"output_{safe_symbol}_{args.start}_{args.end}"
    os.makedirs(outdir, exist_ok=True)

    print(f"Resolved symbol: {symbol}  |  Exchange: {exchange}  |  Currency: {currency}")

    raw = download_data(symbol, args.start, args.end, outdir)
    enriched = run_descriptive_analysis(raw, symbol, args.recent_years, outdir, currency=currency)
    run_backtest(enriched, symbol, args.recent_years, args.capital, args.lot_size,
                 args.sma_fast, args.sma_slow, outdir, currency=currency)

    print(f"\nAll done. Results saved in: {outdir}/")


if __name__ == "__main__":
    main()
