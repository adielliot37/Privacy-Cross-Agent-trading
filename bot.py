

import random
import json
import datetime
from typing import Any

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import TELEGRAM_TOKEN, RISK_REWARD_RATIO
from indicators import (
    fetch_top_symbols,
    fetch_historical,
    calculate_indicators,
    analyze_signals,
    determine_signal,
    calculate_entry_exit,
    detect_trend
)
from ai_module import fetch_ai_overview, summarize_via_gpt
from trade_executor import open_position
from storage import load_trades, save_trades, upload_to_storacha

# Helper to safely convert values to float
def safe_get(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except:
        return default

# ──────────────────────────────────────────────────────────────────────────────
async def auto_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /auto → pick a random top-20 non-stable USDT symbol,
    generate a signal, place a $10×5× margin order on Binance Futures,
    format a concise report, upload it to Storacha, log in trades.json, and reply.
    """
    await update.message.reply_text("🔄 Generating signal & executing trade…")

    
    try:
        symbols = fetch_top_symbols(count=20)
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching symbols: {e}")
        return

    if not symbols:
        await update.message.reply_text("❌ No valid symbols found.")
        return

    symbol = None
    df = None
    for _ in range(5):
        candidate = random.choice(symbols)
        tmp_df = fetch_historical(candidate, timeframe="1h", limit=200)
        if tmp_df.empty:
            continue
        tmp_df = calculate_indicators(tmp_df)
        last_close = tmp_df.iloc[-1]["close"] if not tmp_df.empty else 0
        if last_close > 0:
            symbol = candidate
            df = tmp_df
            break

    if symbol is None or df is None or df.empty:
        await update.message.reply_text("❌ Unable to find a valid trading pair.")
        return

   
    scores = analyze_signals(df)
    signal, strength = determine_signal(scores)

    
    if signal == "Neutral":
        await update.message.reply_text(f"Signal is Neutral for {symbol}. No trade opened.")
        return

    
    try:
        order = open_position(symbol, side=signal)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to open position: {e}")
        return

    
    ai_overview = fetch_ai_overview(symbol)

   
    trend_str = detect_trend(df)
    gpt_prompt = (
        f"Based on technical analysis for {symbol}:\n"
        f"Signal: {signal} (strength: {strength:.2f}/5)\n"
        f"Order Info: {order}\n\n"
        f"Token Metrics AI: {ai_overview}\n"
        f"Trend: {trend_str}.\n"
    )
    try:
        sentiment = summarize_via_gpt(
            "You are an expert crypto trading analyst. Provide a concise 2–3 sentence recommendation.",
            gpt_prompt,
        )
    except Exception as e:
        sentiment = f"Unable to generate summary: {e}"

   
    entry_price, stop_loss, take_profit = calculate_entry_exit(df, signal)
    entry_price = safe_get(entry_price)
    stop_loss   = safe_get(stop_loss)
    take_profit = safe_get(take_profit)

    # Compute percentages
    sl_pct = f"{abs(stop_loss - entry_price)/entry_price*100:.2f}%" if entry_price else "N/A"
    tp_pct = f"{abs(take_profit - entry_price)/entry_price*100:.2f}%" if entry_price else "N/A"

    concise_lines = [
        f"Pair:         {symbol}",
        f"Signal:       {signal} (Strength: {strength:.2f}/5)",
        f"Entry Price:  {entry_price:.4f}",
        f"Stop Loss:    {stop_loss:.4f} ({sl_pct})",
        f"Take Profit:  {take_profit:.4f} ({tp_pct})",
        f"Risk-Reward:  1:{RISK_REWARD_RATIO:.1f}",
        "------------------------------------------------------------",
        f"AI Summary:   {sentiment}"
    ]
    final_text = "\n".join(concise_lines)

  
    cid = upload_to_storacha(final_text)

   
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rec = {
        "symbol": symbol,
        "datetime": ts,
        "cid": cid
    }
    trades = load_trades()
    trades.append(rec)
    save_trades(trades)

   
    await update.message.reply_text(final_text)
    if cid.startswith("Error"):
        await update.message.reply_text(f"⚠️ Upload failed: {cid}")
    else:
        ipfs_url = f"https://ipfs.io/ipfs/{cid}"
        await update.message.reply_text(f"📨 Uploaded to Storacha: {ipfs_url}")

async def trades_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /trades → read trades.json and list each as:
    “1. SYMBOL, YYYY-MM-DD HH:MM:SS, https://ipfs.io/ipfs/CID”
    """
    trades = load_trades()
    if not trades:
        await update.message.reply_text("No trades recorded yet.")
        return

    lines = []
    for idx, rec in enumerate(trades, start=1):
        sym = rec.get("symbol", "N/A")
        dt  = rec.get("datetime", "N/A")
        cid = rec.get("cid", "")
        url = f"https://ipfs.io/ipfs/{cid}" if not cid.startswith("Error") else cid
        lines.append(f"{idx}. {sym}, {dt}, {url}")

    chunk_size = 50
    for i in range(0, len(lines), chunk_size):
        await update.message.reply_text("\n".join(lines[i:i+chunk_size]))

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("auto", auto_handler))
    app.add_handler(CommandHandler("trades", trades_handler))
    print("Bot is running…")
    app.run_polling()
