import os
import asyncio
from flask import Flask, render_template_string
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

# --- Flask App ---
app = Flask(__name__)

# Miner HTML (we’ll serve this directly here for simplicity)
with open("miner.html", "r") as f:
    MINER_HTML = f.read()

@app.route("/")
def index():
    return MINER_HTML

# --- Telegram Bot ---
async def start(update, context):
    await update.message.reply_text("Welcome! The mini app is live here:\n"
                                    "👉 https://ton-usdt-miner-production.up.railway.app/")

def setup_bot() -> Application:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    return application

# --- Async Runner ---
async def main():
    application = setup_bot()

    # Run bot in background
    asyncio.create_task(application.run_polling())

    # Run Flask inside loop
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    )

if __name__ == "__main__":
    asyncio.run(main())
