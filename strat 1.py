"""
============================================================================
STRATEGY 1 - TELEGRAM SIGNAL BOT
Liquidity Sweep + MSS + Displacement + 0.5 Fibonacci Retracement
============================================================================
Receives webhook alerts from TradingView and sends formatted signals
to a Telegram chat/channel.

SETUP:
1. pip install flask python-telegram-bot requests
2. Create a Telegram bot via @BotFather -> get your BOT_TOKEN
3. Get your chat ID via @userinfobot or @getmyid_bot -> CHAT_ID
4. Set environment variables or edit config below
5. Deploy to a server (Railway, Render, VPS, etc.)
6. Point TradingView alert webhook URL to: http://your-server:5001/webhook
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

# Telegram Bot Config - SET THESE
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

# Server Config
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5001))

# Webhook Secret (optional security layer)
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot1_signals.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)

# ============================================================================
# TELEGRAM MESSAGING
# ============================================================================

def send_telegram_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to Telegram chat."""
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
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(f"Telegram API error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def format_signal_message(data: dict) -> str:
    """Format the trading signal into a beautiful Telegram message."""
    
    signal = data.get("signal", "UNKNOWN")
    symbol = data.get("symbol", "N/A")
    timeframe = data.get("timeframe", "N/A")
    entry = data.get("entry", 0)
    sl = data.get("sl", 0)
    tp = data.get("tp", 0)
    rr = data.get("rr", 0)
    sweep_level = data.get("sweep_level", 0)
    
    # Calculate risk in ticks/points
    if signal == "LONG":
        risk_ticks = round((entry - sl) / 0.25) if entry and sl else 0
        reward_ticks = round((tp - entry) / 0.25) if tp and entry else 0
    else:
        risk_ticks = round((sl - entry) / 0.25) if sl and entry else 0
        reward_ticks = round((entry - tp) / 0.25) if entry and tp else 0
    
    # Direction emoji
    direction_emoji = "🟢" if signal == "LONG" else "🔴"
    arrow = "⬆️" if signal == "LONG" else "⬇️"
    
    # Timestamp
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    message = f"""
{direction_emoji} <b>SIGNAL: {signal}</b> {arrow}
━━━━━━━━━━━━━━━━━━━━━

📊 <b>Strategy:</b> Liquidity Sweep + MSS + Fib
📈 <b>Symbol:</b> {symbol}
⏱ <b>Timeframe:</b> {timeframe}

💰 <b>Entry:</b> {entry}
🛑 <b>Stop Loss:</b> {sl}
🎯 <b>Take Profit:</b> {tp}

📐 <b>Risk:Reward:</b> 1:{rr}
📉 <b>Risk:</b> {risk_ticks} ticks
📈 <b>Reward:</b> {reward_ticks} ticks

🔍 <b>Sweep Level:</b> {sweep_level}

━━━━━━━━━━━━━━━━━━━━━
🕐 {now}
⚠️ <i>Confirm with order flow before entry</i>
"""
    return message.strip()


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive TradingView webhook alert and forward to Telegram."""
    try:
        # Security check (optional)
        if WEBHOOK_SECRET:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {WEBHOOK_SECRET}":
                logger.warning("Unauthorized webhook attempt")
                return jsonify({"error": "Unauthorized"}), 401
        
        # Parse incoming data
        raw_data = request.get_data(as_text=True)
        logger.info(f"Received webhook: {raw_data}")
        
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            # TradingView sometimes sends plain text
            data = {"signal": raw_data, "symbol": "UNKNOWN"}
        
        # Validate strategy
        strategy = data.get("strategy", "")
        if strategy != "LiqSweep_MSS_Fib":
            logger.info(f"Ignoring non-matching strategy: {strategy}")
            return jsonify({"status": "ignored"}), 200
        
        # Format and send
        message = format_signal_message(data)
        success = send_telegram_message(message)
        
        if success:
            return jsonify({"status": "sent"}), 200
        else:
            return jsonify({"error": "Failed to send"}), 500
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "running",
        "strategy": "Liquidity Sweep + MSS + Displacement + 0.5 Fib",
        "bot": "Strategy 1",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route("/test", methods=["GET"])
def test_signal():
    """Send a test signal to verify Telegram connection."""
    test_data = {
        "strategy": "LiqSweep_MSS_Fib",
        "signal": "LONG",
        "symbol": "CME_MINI:NQ1!",
        "timeframe": "5",
        "entry": 21250.00,
        "sl": 21220.00,
        "tp": 21310.00,
        "rr": 2.0,
        "sweep_level": 21215.50,
        "time": str(datetime.now(timezone.utc).timestamp())
    }
    
    message = "🧪 <b>TEST SIGNAL</b> 🧪\n\n" + format_signal_message(test_data)
    success = send_telegram_message(message)
    
    if success:
        return jsonify({"status": "test sent"}), 200
    else:
        return jsonify({"error": "test failed"}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Strategy 1 Bot - Liquidity Sweep MSS Fib")
    logger.info(f"Starting server on {HOST}:{PORT}")
    logger.info(f"Webhook URL: http://YOUR_SERVER:{PORT}/webhook")
    logger.info(f"Test URL: http://YOUR_SERVER:{PORT}/test")
    logger.info("=" * 60)
    
    # Startup notification
    send_telegram_message("🤖 <b>Bot Started</b>\n\nStrategy 1: Liquidity Sweep + MSS + Fib\nListening for signals...")
    
    app.run(host=HOST, port=PORT, debug=False)
