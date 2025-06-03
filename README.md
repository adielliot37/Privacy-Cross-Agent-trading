# Autonomous Trading Bot with Storacha MCP & Token Metrics AI

This project demonstrates a live, multi-component crypto trading pipeline using the MCP with Storacha for decentralized file storage, Token Metrics AI for signal generation, and OpenAI GPT-4 for concise trade summaries. When a clear Long/Short signal is generated

## Tech Stack

- **Python 3.12**
- **CCXT** for Binance Futures connectivity
- **Pandas + pandas_ta** for technical indicators (RSI, MACD, Bollinger Bands, ATR, Stochastic, ADX, CCI)
- **OpenAI GPT-4** for trade rationale
- **Token Metrics API** for AI-driven Long/Short overview
- **Storacha MCP Storage Server** (REST mode) for decentralized, CID-based file storage
- **python-telegram-bot** for Telegram command interface
- **(Upcoming)** UCAN-based authorization for enhanced privacy and permissioned uploads

## Agent Roles & Flow

This project simulates three collaborating agents that operate in sequence:

| Agent | Task |
|-------|------|
| Agent A | Fetch top-20 USDT pairs, compute indicators, generate Long/Short signal |
| Agent B | On a clear signal, open a $10 USD market order @ 5× leverage on Binance Futures |
| Agent C | Upload concise "signal + trade details + AI summary" report to Storacha |

### Agent A

- Retrieves 1h OHLCV from Binance (CCXT) for a random top-20 USDT pair (excludes stable bases).
- Calculates:
  - RSI(14) (oversold < 35, overbought > 65)
  - MACD histogram crossover
  - EMA20/EMA50 crossover
  - Bollinger Bands extremes
  - Stochastic (K/D)
  - ADX(14) for trend strength
  - CCI(14)
- Combines weights: if |Long − Short| > 0.5 → a decisive "Long" or "Short" signal; otherwise "Neutral."

### Agent B

Receives the signal. If not Neutral:
- Sets 5× leverage on Binance Futures (USDT-M).
- Computes contract size: ($10 × 5) ÷ price.
- Places a market order (buy for Long, sell for Short).

### Agent C

Formats a concise report:

```
Pair:         ETH/USDT  
Signal:       Short (Strength: 2.00/5)  
Entry Price:  0.0677  
Stop Loss:    0.0717 (6.00%)  
Take Profit:  0.0595 (11.99%)  
Risk-Reward:  1:2.0  
------------------------------------------------------------  
AI Summary:   Recommendation to short at 0.0677 with stop at 0.0717…  
```

- Uploads that text to Storacha MCP (REST) via a Base64 → JSON-RPC `tools/call` → "upload" call.
- Receives a CID, constructs `https://ipfs.io/ipfs/{CID}`, and logs `{symbol, datetime, CID}` in `trades.json`.

## How MCP + Storacha Works

### Flow

1. Agent C writes the report to a temporary file, Base64-encodes it, and calls MCP REST `tools/call` → "upload".
2. MCP stores the file (authorized by UCAN once integrated) into a Storacha Space.
3. The file receives a CID (content ID).
4. Agent A or Agent B can retrieve it via MCP REST `tools/call` → "retrieve" using the CID.
5. Data flows trustlessly without hardcoded file paths or centralized APIs.

### MCP Tool Calls Used

- `tools/call` → "upload": stores file as Base64 + filename → returns CID
- `tools/call` → "retrieve": fetches file by CID + filename
- `tools/call` → "identity": retrieves the active DID key (optional)

## Setup Instructions

### 1. Clone & Setup Project

```bash
git clone https://github.com/adielliot37/Privacy-Cross-Agent-trading.git
cd Privacy-Cross-Agent-trading
```

### 2. Create .env File

```bash
echo "TELEGRAM_BOT_TOKEN=your_telegram_token"        >> .env
echo "TM_API_KEY=your_tokenmetrics_api_key"         >> .env
echo "OPENAI_API_KEY=your_openai_api_key"           >> .env
echo "MCP_REST_URL=http://localhost:3001/rest"      >> .env
echo "BINANCE_API_KEY=your_binance_api_key"         >> .env
echo "BINANCE_SECRET_KEY=your_binance_secret_key"   >> .env
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Storacha MCP Storage Server (REST Mode)

```bash
cd mcp-storage-server
pnpm install

# (Optional) Generate UCAN delegation once ready
# w3 delegation create <agent_id> --can 'store/add' --can 'upload/add' --base64

export PRIVATE_KEY=your_private_key_base64
export DELEGATION=your_base64_delegation
export MCP_TRANSPORT_MODE=rest
export MCP_SERVER_PORT=3001
pnpm start:rest

# Server will run at http://localhost:3001/rest
```

### 5. Run the Bot

```bash
cd Privacy-Cross-Agent-trading
python bot.py
```

## Live Demo Flow

### `/auto`

1. Bot picks a random top-20 pair, calculates indicators, generates a signal.
2. If Long/Short, it opens a $10, 5× market order on Binance Futures.
3. Formats a concise report and uploads it to Storacha.
4. Replies in Telegram:

```
Pair:         ETH/USDT
Signal:       Short (Strength: 2.00/5)
Entry Price:  0.0677
Stop Loss:    0.0717 (6.00%)
Take Profit:  0.0595 (11.99%)
Risk-Reward:  1:2.0
------------------------------------------------------------
AI Summary:   Recommendation to short at 0.0677 with stop at 0.0717…
📨 Uploaded to Storacha: https://ipfs.io/ipfs/bafy…
```

### `/trades`

Lists past entries from `trades.json`:

```
1. ETH/USDT, 2025-06-03 15:22:44, https://ipfs.io/ipfs/bafy…
2. SOL/USDT, 2025-06-03 15:40:12, https://ipfs.io/ipfs/bafy…
```

## Notes

- **Indicator Logic**: Weighted combination of RSI, MACD hist crossover, EMA cross, Bollinger Bands, Stochastic, ADX, and CCI.
- **Trading Logic**: $10 USD market order at 5× leverage → quantity = ($10 × 5) ÷ price.
- **UCAN Integration**: Coming soon to restrict MCP uploads/retrieval via capability proofs.
- **Security**: Keep your `.env` file private. Use Binance API keys with Futures-only trading permissions (no withdrawal).



Cheers ☕
