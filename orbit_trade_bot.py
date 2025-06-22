import requests
import pandas as pd
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ParseMode

BOT_TOKEN = "7397317010:AAE41dwNOzYF8pxsZiOITCdhULQ7GJpHcUY"
CHAT_ID = "1917297411"

# --- RSI Calculation ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- EMA Trend ---
def calculate_ema(series, period=50):
    return series.ewm(span=period, adjust=False).mean()

# --- Analyze Binance Chart ---
def analyze_binance_chart(symbol="BTCUSDT", interval="15m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)

    if response.status_code != 200:
        return None, None, None, None

    candles = response.json()
    if not candles:
        return None, None, None, None

    df = pd.DataFrame(candles, columns=[
        "time", "open", "high", "low", "close", "volume",
        "_", "_", "_", "_", "_", "_"
    ])
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    df["rsi"] = calculate_rsi(df["close"])
    df["ema"] = calculate_ema(df["close"])

    last_price = df["close"].iloc[-1]
    rsi = df["rsi"].iloc[-1]
    ema = df["ema"].iloc[-1]
    trend = "Bullish" if last_price > ema else "Bearish"

    if rsi > 70:
        signal = "SHORT (Overbought)"
        reason = f"RSI is {rsi:.2f} (Overbought) and price is {'above' if last_price > ema else 'below'} EMA → Reversal expected"
    elif rsi < 30:
        signal = "LONG (Oversold)"
        reason = f"RSI is {rsi:.2f} (Oversold) and price is {'above' if last_price > ema else 'below'} EMA → Bounce likely"
    else:
        signal = "WAIT (Neutral)"
        reason = f"RSI is {rsi:.2f}, no strong reversal zone. Price is {trend}"

    return signal, last_price, reason, trend

# --- Message Handler ---
def handle_message(update, context):
    text = update.message.text.lower()

    if "trade" in text:
        for asset in ["BTCUSDT", "ETHUSDT"]:
            tf = "15m"
            signal, price, reason, trend = analyze_binance_chart(asset, tf)

            if signal:
                sl = round(price + 300, 2) if "SHORT" in signal else round(price - 300, 2)
                tp1 = round(price - 600, 2) if "SHORT" in signal else round(price + 600, 2)
                tp2 = round(price - 1200, 2) if "SHORT" in signal else round(price + 1200, 2)

                msg = (
                    f"📊 *Binance Signal — Live*\n\n"
                    f"Asset: {asset}\n"
                    f"TF: {tf}\n"
                    f"Price: ${price:.2f}\n"
                    f"Signal: {signal}\n"
                    f"🎯 Entry: {round(price, 2)}\n"
                    f"❌ SL: {sl}\n"
                    f"✅ TP1: {tp1}\n"
                    f"✅ TP2: {tp2}\n"
                    f"📈 Trend: {trend}\n"
                    f"🧠 Reason: {reason}\n"
                    f"🎯 Strategy: RR = 1:2 (Fixed SL/TP Logic)\n"
                    f"🕒 Valid for 30–45 mins"
                )
                context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.MARKDOWN)

# --- Start Polling ---
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    print("✅ Bot is running... type 'trade' in Telegram!")
    updater.idle()

if __name__ == "__main__":
    main()
