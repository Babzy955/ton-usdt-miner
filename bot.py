import logging
import asyncio
from flask import Flask, send_from_directory
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ==============================
# CONFIG
# ==============================
TOKEN = "8235411673:AAGJBuKA0Y2PIGr06f12onmdRNX472123kc"  # <- replace with your bot token
PORT = 8080  # Flask server port

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ==============================
# FLASK APP
# ==============================
app = Flask(__name__)

@app.route("/")
def serve_miner():
    return send_from_directory(".", "miner.html")

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(".", filename)

# ==============================
# TELEGRAM HANDLERS
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a button that opens the WebApp."""
    keyboard = [
        [KeyboardButton("🚀 Open Miner", web_app=WebAppInfo(url="https://ton-usdt-miner-production.up.railway.app/"))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Welcome! Tap below to open the USDT Miner ⬇️",
        reply_markup=reply_markup,
    )

# ==============================
# MAIN ENTRY
# ==============================
async def run_bot():
    """Run the Telegram bot."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    await application.run_polling()

async def run_flask():
    """Run the Flask web server."""
    app.run(host="0.0.0.0", port=PORT)

async def main():
    await asyncio.gather(run_bot(), run_flask())

if __name__ == "__main__":
    asyncio.run(main())
