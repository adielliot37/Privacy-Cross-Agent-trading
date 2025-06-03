import numpy as np
np.NaN = np.nan

import ccxt
import pandas as pd
import pandas_ta as ta

from config import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BOLLINGER_PERIOD, BOLLINGER_STD,
    ATR_PERIOD
)

def fetch_top_symbols(count: int = 20) -> list[str]:
    """
    Return the top `count` USDT pairs by volume, excluding stablecoin bases.
    """
    STABLE_BASES = {"USDC", "BUSD", "DAI", "USDP", "TUSD", "USDT"}
    exchange = ccxt.binance({"enableRateLimit": True})
    tickers = exchange.fetch_tickers()
    usdt_pairs = {
        sym: data
        for sym, data in tickers.items()
        if sym.endswith("/USDT") and data.get("quoteVolume") is not None
    }
    sorted_pairs = sorted(
        usdt_pairs.items(),
        key=lambda kv: kv[1]["quoteVolume"],
        reverse=True
    )
    top_symbols = [sym for sym, _ in sorted_pairs[:count]]
    return [s for s in top_symbols if s.split("/")[0] not in STABLE_BASES]

def fetch_historical(symbol: str, timeframe="1h", limit=200) -> pd.DataFrame:
    """
    Fetch up to `limit` 1h candles for `symbol` from Binance.
    """
    try:
        ex = ccxt.binance({"enableRateLimit": True})
        ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=["ts", "open", "high", "low", "close", "vol"])
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df.set_index("ts", inplace=True)
        for col in ["open", "high", "low", "close", "vol"]:
            df[col] = df[col].astype(float)
        return df
    except Exception as e:
        print(f"[fetch_historical] Error for {symbol}: {e}")
        return pd.DataFrame()

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add RSI, MACD, Bollinger Bands, ATR, Stoch, ADX, OBV, CCI via pandas_ta.
    """
    if df.empty:
        return df

    df = df.copy()
    df.rename(columns={"vol": "volume"}, inplace=True)

    strategy = ta.Strategy(
        name="Multi-Indicator",
        description="SMA/EMA/RSI/MACD/BB/ATR/Stoch/ADX/OBV/CCI",
        ta=[
            {"kind": "sma",   "length": 20},
            {"kind": "sma",   "length": 50},
            {"kind": "ema",   "length": 20},
            {"kind": "ema",   "length": 50},
            {"kind": "rsi",   "length": RSI_PERIOD},
            {"kind": "macd",  "fast": MACD_FAST, "slow": MACD_SLOW, "signal": MACD_SIGNAL},
            {"kind": "bbands","length": BOLLINGER_PERIOD, "std": BOLLINGER_STD},
            {"kind": "atr",   "length": ATR_PERIOD},
            {"kind": "stoch", "k": 14, "d": 3, "smooth_k": 3},
            {"kind": "adx",   "length": 14},
            {"kind": "obv"},
            {"kind": "cci",   "length": 14},
        ]
    )
    df.ta.strategy(strategy)

    # In case ATR or CCI weren’t auto-added:
    if "ATR_14" not in df.columns:
        df["ATR_14"] = ta.atr(high=df["high"], low=df["low"], close=df["close"], length=ATR_PERIOD)
    if "CCI_14" not in df.columns:
        df["CCI_14"] = ta.cci(high=df["high"], low=df["low"], close=df["close"], length=14)

    mapping = {
        "RSI_14":      "rsi",
        "ATR_14":      "atr",
        "SMA_20":      "sma20",
        "SMA_50":      "sma50",
        "EMA_20":      "ema20",
        "EMA_50":      "ema50",
        "BBL_20_2.0":  "bb_lower",
        "BBM_20_2.0":  "bb_middle",
        "BBU_20_2.0":  "bb_upper",
        "MACD_12_26_9":     "macd",
        "MACDs_12_26_9":    "macd_signal",
        "MACDh_12_26_9":    "macd_hist",
        "STOCHk_14_3_3":    "stoch_k",
        "STOCHd_14_3_3":    "stoch_d",
        "ADX_14":           "adx",
        "CCI_14":           "cci",
    }
    to_rename = {k: v for k, v in mapping.items() if k in df.columns}
    df.rename(columns=to_rename, inplace=True)

    return df

def analyze_signals(df: pd.DataFrame) -> dict:
    """
    Return {"long": score, "short": score} based on the last two candles.
    """
    if df.empty or len(df) < 2:
        return {"long": 0.0, "short": 0.0}

    curr, prev = df.iloc[-1], df.iloc[-2]
    signals = {"long": 0.0, "short": 0.0}

    # RSI
    if "rsi" in curr:
        if curr["rsi"] < RSI_OVERSOLD:
            signals["long"] += 2
        elif curr["rsi"] > RSI_OVERBOUGHT:
            signals["short"] += 2

    # MACD histogram crossover
    if "macd_hist" in curr and "macd_hist" in prev:
        if curr["macd_hist"] > 0 and prev["macd_hist"] < 0:
            signals["long"] += 2
        elif curr["macd_hist"] < 0 and prev["macd_hist"] > 0:
            signals["short"] += 2

    # EMA cross
    if all(k in curr for k in ["close", "ema20", "ema50"]):
        if curr["close"] > curr["ema20"] > curr["ema50"]:
            signals["long"] += 0.5
        elif curr["close"] < curr["ema20"] < curr["ema50"]:
            signals["short"] += 0.5

    # Bollinger Bands
    if all(k in curr for k in ["close", "bb_lower", "bb_upper"]):
        if curr["close"] < curr["bb_lower"]:
            signals["long"] += 0.75
        elif curr["close"] > curr["bb_upper"]:
            signals["short"] += 0.75

    # Stochastic
    if all(k in curr for k in ["stoch_k", "stoch_d"]):
        if curr["stoch_k"] < 20 and curr["stoch_d"] < 20:
            signals["long"] += 0.5
        elif curr["stoch_k"] > 80 and curr["stoch_d"] > 80:
            signals["short"] += 0.5

    # ADX
    if "adx" in curr and curr["adx"] > 25:
        if signals["long"] > signals["short"]:
            signals["long"] += 0.5
        elif signals["short"] > signals["long"]:
            signals["short"] += 0.5

    # CCI
    if "cci" in curr:
        if curr["cci"] < -100:
            signals["long"] += 0.5
        elif curr["cci"] > 100:
            signals["short"] += 0.5

    return signals

def determine_signal(signals: dict) -> tuple[str, float]:
    """
    Given {"long": x, "short": y}, return:
      - ("Long",  |x−y|) if x > y + 0.5
      - ("Short", |y−x|) if y > x + 0.5
      - ("Neutral", |x−y|) otherwise
    """
    long_s = signals.get("long", 0.0)
    short_s = signals.get("short", 0.0)
    strength = abs(long_s - short_s)
    if long_s > short_s + 0.5:
        return "Long", strength
    elif short_s > long_s + 0.5:
        return "Short", strength
    else:
        return "Neutral", strength

def calculate_entry_exit(df: pd.DataFrame, signal: str) -> tuple[float, float, float]:
    """
    Use ATR (or 1% fallback) to set entry, stop loss, and take profit.
    """
    if df.empty or signal == "Neutral":
        return 0.0, 0.0, 0.0

    curr = df.iloc[-1]
    entry_price = curr["close"]
    if entry_price <= 0:
        return 0.0, 0.0, 0.0

    atr_val = curr.get("atr", None)
    if atr_val is None or pd.isna(atr_val) or atr_val <= 0:
        atr_val = entry_price * 0.01
    atr_mult = 1.3

    if signal == "Long":
        stop_loss   = entry_price - (atr_val * atr_mult)
        take_profit = entry_price + ((entry_price - stop_loss) * (2.0))  # RISK_REWARD_RATIO=2.0
    else:  # signal == "Short"
        stop_loss   = entry_price + (atr_val * atr_mult)
        take_profit = entry_price - ((stop_loss - entry_price) * (2.0))

    return entry_price, stop_loss, take_profit

def detect_trend(df: pd.DataFrame) -> str:
    """
    Simple trend:
      - "Bullish" if close > sma50 and sma20 > sma50
      - "Bearish" if close < sma50 and sma20 < sma50
      - Otherwise "Sideways"
    """
    if df.empty:
        return "Unknown"
    curr = df.iloc[-1]
    if not all(k in curr for k in ["close", "sma20", "sma50"]):
        return "Unknown"
    if curr["close"] > curr["sma50"] and curr["sma20"] > curr["sma50"]:
        return "Bullish"
    elif curr["close"] < curr["sma50"] and curr["sma20"] < curr["sma50"]:
        return "Bearish"
    return "Sideways"
