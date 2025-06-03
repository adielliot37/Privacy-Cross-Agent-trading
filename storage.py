
import os
import json
import tempfile
import base64
import requests

from config import MCP_REST_URL

TRADES_FILE = "trades.json"

def load_trades() -> list[dict]:
    if os.path.isfile(TRADES_FILE):
        try:
            with open(TRADES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_trades(trades: list[dict]):
    with open(TRADES_FILE, "w") as f:
        json.dump(trades, f, indent=2)

def upload_to_storacha(content: str) -> str:
    """
    Writes `content` to a temp file, base64-encodes it, then calls MCP REST upload.
    Returns the IPFS CID string or an error message starting with "Error".
    """
    try:
        
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".txt") as tmp:
            tmp.write(content.encode("utf-8"))
            tmp.flush()
            tmp_path = tmp.name

       
        with open(tmp_path, "rb") as f:
            b64data = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "jsonrpc": "2.0",
            "id": "upload-request",
            "method": "tools/call",
            "params": {
                "name": "upload",
                "arguments": {
                    "file": b64data,
                    "name": os.path.basename(tmp_path)
                }
            }
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(MCP_REST_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

        rpc_resp = resp.json()
        text_payload = rpc_resp["result"]["content"][0]["text"]
        tool_output = json.loads(text_payload)

        cid = tool_output.get("root", {}).get("/", None)
        if cid:
            return cid
        files_dict = tool_output.get("files", {})
        if files_dict:
            first_file = next(iter(files_dict))
            return files_dict[first_file]["/"]
        return "No CID found"
    except Exception as e:
        return f"Error uploading to Storacha: {e}"
