
import os
from dotenv import load_dotenv

load_dotenv()  # reads .env

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

# TokenMetrics
TM_API_KEY = os.getenv("TM_API_KEY", "").strip()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Storacha MCP (REST)
MCP_REST_URL = os.getenv("MCP_REST_URL", "").strip()

# Binance Futures credentials
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "").strip()
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "").strip()

# Globals for indicators/trading
RSI_PERIOD        = 14
RSI_OVERSOLD      = 35
RSI_OVERBOUGHT    = 65
MACD_FAST         = 12
MACD_SLOW         = 26
MACD_SIGNAL       = 9
BOLLINGER_PERIOD  = 20
BOLLINGER_STD     = 2
ATR_PERIOD        = 14
RISK_REWARD_RATIO = 2.0   # target profit is 2× stop-loss distance
TRADE_USD_SIZE    = 10.0  # $10 
LEVERAGE          = 5     # 5× 
