import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask, send_from_directory
import threading
import os

# ---------------------------
# CONFIG
# ---------------------------
BOT_TOKEN = "8235411673:AAGJBuKA0Y2PIGr06f12onmdRNX472123kc"  # replace with your token

# Balance (mining simulation)
user_balances = {}
MINING_RATE = 0.000001  # USDT per second per user (adjust for 3% every 3 months)

# ---------------------------
# MINER LOOP
# ---------------------------
async def miner_loop():
    while True:
        for user_id in user_balances:
            user_balances[user_id] += MINING_RATE
        await asyncio.sleep(1)  # mine every second

# ---------------------------
# BOT COMMANDS
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_balances:
        user_balances[user_id] = 0.0

    keyboard = [
        [
            InlineKeyboardButton(
                "💰 Open Miner App",
                web_app=WebAppInfo(url="https://ton-usdt-miner-production.up.railway.app/miner")
            )
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Welcome {update.effective_user.first_name}! Your miner is ready. "
        "Click below to view your balance and info.",
        reply_markup=reply_markup
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    balance = user_balances.get(user_id, 0.0)
    await query.edit_message_text(f"📊 Your current balance: {balance:.8f} USDT")

# ---------------------------
# FLASK APP (Mini App hosting)
# ---------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot and Mini App are running!"

@app.route("/miner")
def miner():
    return send_from_directory("static", "miner.html")

@app.route("/miner.js")
def miner_js():
    return send_from_directory("static", "miner.js")

@app.route("/style.css")
def style_css():
    return send_from_directory("static", "style.css")

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# ---------------------------
# MAIN
# ---------------------------
async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(stats, pattern="stats"))

    # start mining loop
    application.create_task(miner_loop())

    # run bot
    await application.run_polling()

if __name__ == "__main__":
    # start flask in a thread
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
