"""
============================================================================
STRATEGY 3 - TELEGRAM SIGNAL BOT
Volume Profile Failed Auction
"Value Area Reclaim + Absorption Continuation Model"
============================================================================
Receives webhook alerts from TradingView and sends formatted signals.

SETUP:
1. pip install flask requests
2. Create Telegram bot via @BotFather -> get BOT_TOKEN
3. Get chat ID -> CHAT_ID
4. Set env vars or edit below
5. Deploy. Webhook URL: http://your-server:5003/webhook
============================================================================
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

# ============================================================================
# CONFIGURATION
# ============================================================================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_S3", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_S3", "YOUR_CHAT_ID_HERE")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT_S3", 5003))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET_S3", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot3_signals.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================================
# TELEGRAM
# ============================================================================

def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Telegram message sent")
            return True
        else:
            logger.error(f"Telegram error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Send failed: {e}")
        return False


def format_signal(data: dict) -> str:
    signal      = data.get("signal", "UNKNOWN")
    symbol      = data.get("symbol", "N/A")
    timeframe   = data.get("timeframe", "N/A")
    entry       = data.get("entry", 0)
    sl          = data.get("sl", 0)
    tp          = data.get("tp", 0)
    rr          = data.get("rr", 0)
    vah         = data.get("vah", 0)
    val_level   = data.get("val", 0)
    poc_level   = data.get("poc", 0)
    auction_ext = data.get("auction_extreme", 0)
    migration   = data.get("migration", "N/A")
    absorb      = data.get("absorb_count", 0)
    bars_out    = data.get("bars_outside", 0)
    tp_mode     = data.get("tp_mode", "N/A")
    
    # Risk in ticks
    if signal == "LONG":
        risk_ticks   = round((entry - sl) / 0.25) if entry and sl else 0
        reward_ticks = round((tp - entry) / 0.25) if tp and entry else 0
    else:
        risk_ticks   = round((sl - entry) / 0.25) if sl and entry else 0
        reward_ticks = round((entry - tp) / 0.25) if entry and tp else 0
    
    emoji = "🟢" if signal == "LONG" else "🔴"
    arrow = "⬆️" if signal == "LONG" else "⬇️"
    
    # Migration emoji
    mig_emoji = "📈" if migration == "BULLISH" else "📉" if migration == "BEARISH" else "➡️"
    
    # Auction quality
    if absorb >= 4:
        auction_quality = "🏛️ STRONG ABSORPTION"
    elif absorb >= 3:
        auction_quality = "🏛️ CLEAR ABSORPTION"
    elif absorb >= 2:
        auction_quality = "🏛️ CONFIRMED"
    else:
        auction_quality = "⚠️ MINIMAL"
    
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    message = f"""
{emoji} <b>FAILED AUCTION: {signal}</b> {arrow}
━━━━━━━━━━━━━━━━━━━━━

📊 <b>Strategy:</b> Value Area Reclaim
📈 <b>Symbol:</b> {symbol}
⏱ <b>Timeframe:</b> {timeframe}

{mig_emoji} <b>Value Migration:</b> {migration}
🎯 <b>TP Mode:</b> {tp_mode}

💰 <b>Entry:</b> {entry}
🛑 <b>Stop Loss:</b> {sl}
🎯 <b>Take Profit:</b> {tp}

📐 <b>Risk:Reward:</b> 1:{rr}
📉 <b>Risk:</b> {risk_ticks} ticks
📈 <b>Reward:</b> {reward_ticks} ticks

━━━ <b>AUCTION DATA</b> ━━━

🔴 <b>VAH:</b> {vah}
🟡 <b>POC:</b> {poc_level}
🟢 <b>VAL:</b> {val_level}

📍 <b>Auction Extreme:</b> {auction_ext}
🕐 <b>Bars Outside Value:</b> {bars_out}
🧱 <b>Absorption Candles:</b> {absorb}
💪 <b>Auction Quality:</b> {auction_quality}

━━━━━━━━━━━━━━━━━━━━━
🕐 {now}
⚠️ <i>Verify volume + delta confirm reclaim</i>
"""
    return message.strip()


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        if WEBHOOK_SECRET:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {WEBHOOK_SECRET}":
                return jsonify({"error": "Unauthorized"}), 401
        
        raw = request.get_data(as_text=True)
        logger.info(f"Webhook: {raw}")
        
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"signal": raw, "symbol": "UNKNOWN"}
        
        strategy = data.get("strategy", "")
        if strategy != "FailedAuction_VA":
            logger.info(f"Ignoring: {strategy}")
            return jsonify({"status": "ignored"}), 200
        
        message = format_signal(data)
        success = send_telegram(message)
        return jsonify({"status": "sent" if success else "failed"}), 200 if success else 500
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "running",
        "strategy": "Failed Auction - Value Area Reclaim",
        "bot": "Strategy 3",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route("/test", methods=["GET"])
def test():
    test_data = {
        "strategy": "FailedAuction_VA",
        "signal": "LONG",
        "symbol": "CME_MINI:ES1!",
        "timeframe": "5",
        "entry": 5420.50,
        "sl": 5412.00,
        "tp": 5438.75,
        "rr": 2.15,
        "vah": 5440.00,
        "val": 5418.25,
        "poc": 5428.50,
        "auction_extreme": 5412.00,
        "migration": "BULLISH",
        "absorb_count": 3,
        "bars_outside": 8,
        "tp_mode": "POC",
        "time": str(datetime.now(timezone.utc).timestamp())
    }
    
    msg = "🧪 <b>TEST SIGNAL</b> 🧪\n\n" + format_signal(test_data)
    success = send_telegram(msg)
    return jsonify({"status": "test sent" if success else "test failed"}), 200 if success else 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Strategy 3 Bot - Failed Auction Model")
    logger.info(f"Server: {HOST}:{PORT}")
    logger.info(f"Webhook: http://YOUR_SERVER:{PORT}/webhook")
    logger.info("=" * 60)
    
    send_telegram("🤖 <b>Bot Started</b>\n\nStrategy 3: Failed Auction - Value Area Reclaim\nListening for signals...")
    
    app.run(host=HOST, port=PORT, debug=False)
