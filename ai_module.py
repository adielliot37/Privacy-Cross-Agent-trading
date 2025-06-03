
import requests
import openai
from config import TM_API_KEY, OPENAI_API_KEY


openai.api_key = OPENAI_API_KEY

def fetch_ai_overview(symbol: str) -> str:
    """
    Query TokenMetrics for “long/short” AI overview.
    """
    url = "https://api.tokenmetrics.com/v2/tmai"
    headers = {
        "accept": "application/json",
        "api_key": TM_API_KEY,
        "content-type": "application/json",
    }
    payload = {
        "messages": [
            {
                "user": (
                    f"Should I long or short on {symbol} now "
                    "if yes what should be my entry price and stop loss"
                )
            }
        ]
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("answer", "No AI overview available.")
    except Exception as e:
        return f"Error fetching AI overview: {str(e)}"

def summarize_via_gpt(system_prompt: str, user_prompt: str) -> str:
    """
    Use OpenAI v1.x client to return a 2–3 sentence trading summary.
    """
    try:
        client = openai.OpenAI()
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating summary: {str(e)}"
