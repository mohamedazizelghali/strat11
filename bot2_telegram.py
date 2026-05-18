"""
============================================================================
STRATEGY 2 - TELEGRAM SIGNAL BOT
ICT Liquidity Sweep + Delivery Shift + Inversion Expansion
"9-Point Inversion Model"
============================================================================
Receives webhook alerts from TradingView and sends formatted signals
to a Telegram chat/channel.

SETUP:
1. pip install flask requests
2. Create Telegram bot via @BotFather -> get BOT_TOKEN
3. Get chat ID via @userinfobot -> CHAT_ID
4. Set environment variables or edit config below
5. Deploy to server
6. TradingView webhook URL: http://your-server:5002/webhook
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

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN_S2", "YOUR_BOT_TOKEN_HERE")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID_S2", "YOUR_CHAT_ID_HERE")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT_S2", 5002))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET_S2", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot2_signals.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ============================================================================
# TELEGRAM
# ============================================================================

def send_telegram(text: str, parse_mode: str = "HTML") -> bool:
    """Send message to Telegram."""
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
    """Format trading signal for Telegram."""
    
    signal       = data.get("signal", "UNKNOWN")
    symbol       = data.get("symbol", "N/A")
    timeframe    = data.get("timeframe", "N/A")
    entry        = data.get("entry", 0)
    sl           = data.get("sl", 0)
    tp           = data.get("tp", 0)
    rr           = data.get("rr", 0)
    sweep_level  = data.get("sweep_level", 0)
    sweep_ext    = data.get("sweep_extreme", 0)
    inv_pts      = data.get("inversion_pts", 0)
    entry_mode   = data.get("entry_mode", "N/A")
    
    # Risk in ticks
    if signal == "LONG":
        risk_ticks   = round((entry - sl) / 0.25) if entry and sl else 0
        reward_ticks = round((tp - entry) / 0.25) if tp and entry else 0
    else:
        risk_ticks   = round((sl - entry) / 0.25) if sl and entry else 0
        reward_ticks = round((entry - tp) / 0.25) if entry and tp else 0
    
    emoji     = "🟢" if signal == "LONG" else "🔴"
    arrow     = "⬆️" if signal == "LONG" else "⬇️"
    mode_icon = "⚡" if entry_mode == "Aggressive" else "🎯"
    now       = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Inversion strength rating
    if inv_pts >= 15:
        strength = "🔥🔥🔥 STRONG"
    elif inv_pts >= 12:
        strength = "🔥🔥 SOLID"
    elif inv_pts >= 9:
        strength = "🔥 CONFIRMED"
    else:
        strength = "⚠️ MARGINAL"
    
    message = f"""
{emoji} <b>9-POINT INVERSION: {signal}</b> {arrow}
━━━━━━━━━━━━━━━━━━━━━

📊 <b>Strategy:</b> Sweep + Delivery + Inversion
📈 <b>Symbol:</b> {symbol}
⏱ <b>Timeframe:</b> {timeframe}
{mode_icon} <b>Entry Mode:</b> {entry_mode}

💰 <b>Entry:</b> {entry}
🛑 <b>Stop Loss:</b> {sl}
🎯 <b>Take Profit:</b> {tp}

📐 <b>Risk:Reward:</b> 1:{rr}
📉 <b>Risk:</b> {risk_ticks} ticks
📈 <b>Reward:</b> {reward_ticks} ticks

🔍 <b>Sweep Level:</b> {sweep_level}
📍 <b>Sweep Extreme:</b> {sweep_ext}
🚀 <b>Inversion:</b> {inv_pts:.1f} points
💪 <b>Strength:</b> {strength}

━━━━━━━━━━━━━━━━━━━━━
🕐 {now}
⚠️ <i>Verify delivery shift + delta before entry</i>
"""
    return message.strip()


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    """Receive TradingView webhook and forward to Telegram."""
    try:
        if WEBHOOK_SECRET:
            auth = request.headers.get("Authorization", "")
            if auth != f"Bearer {WEBHOOK_SECRET}":
                logger.warning("Unauthorized webhook")
                return jsonify({"error": "Unauthorized"}), 401
        
        raw = request.get_data(as_text=True)
        logger.info(f"Webhook received: {raw}")
        
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"signal": raw, "symbol": "UNKNOWN"}
        
        strategy = data.get("strategy", "")
        if strategy != "9Point_Inversion":
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
        "strategy": "9-Point Inversion Model",
        "bot": "Strategy 2",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }), 200


@app.route("/test", methods=["GET"])
def test():
    """Send test signal."""
    test_data = {
        "strategy": "9Point_Inversion",
        "signal": "LONG",
        "symbol": "CME_MINI:NQ1!",
        "timeframe": "1",
        "entry": 21285.50,
        "sl": 21248.00,
        "tp": 21360.50,
        "rr": 2.0,
        "sweep_level": 21250.00,
        "sweep_extreme": 21248.00,
        "inversion_pts": 12.5,
        "entry_mode": "Aggressive",
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
    logger.info("Strategy 2 Bot - 9-Point Inversion Model")
    logger.info(f"Server: {HOST}:{PORT}")
    logger.info(f"Webhook: http://YOUR_SERVER:{PORT}/webhook")
    logger.info("=" * 60)
    
    send_telegram("🤖 <b>Bot Started</b>\n\nStrategy 2: 9-Point Inversion Model\nListening for signals...")
    
    app.run(host=HOST, port=PORT, debug=False)
