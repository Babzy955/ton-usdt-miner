import os
import asyncio
from flask import Flask
from telegram.ext import Application, CommandHandler

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

# --- Flask App ---
app = Flask(__name__)

# HTML content directly in Python
MINER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TON-USDT Miner</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0b0f19; color: #fff; text-align: center; padding: 40px; }
        .app-container { background: #1c2233; padding: 30px; border-radius: 12px; box-shadow: 0px 4px 12px rgba(0,0,0,0.6); max-width: 400px; margin: auto; }
        button { padding: 10px 20px; margin: 15px 0; border: none; border-radius: 8px; background: #27ae60; color: #fff; cursor: pointer; font-size: 16px; }
        button:hover { background: #219150; }
        .progress-container { width: 100%; height: 20px; background: #333; border-radius: 10px; overflow: hidden; margin: 20px 0; }
        #progressBar { width: 0%; height: 100%; background: linear-gradient(90deg, #27ae60, #2ecc71); transition: width 0.3s; }
    </style>
</head>
<body>
    <div class="app-container">
        <h1>TON-USDT Miner</h1>
        <p id="status">Press start to begin mining...</p>
        <button id="startBtn">Start Mining</button>
        <div class="progress-container"><div id="progressBar"></div></div>
        <p id="output">Mined: 0 USDT</p>
    </div>
    <script>
        let mining = false;
        let mined = 0;
        document.getElementById("startBtn").addEventListener("click", () => {
            if (!mining) {
                mining = true;
                document.getElementById("status").innerText = "Mining in progress...";
                mine();
            }
        });
        function mine() {
            let progress = 0;
            const progressBar = document.getElementById("progressBar");
            const output = document.getElementById("output");
            const interval = setInterval(() => {
                if (progress < 100) {
                    progress += 2;
                    progressBar.style.width = progress + "%";
                } else {
                    clearInterval(interval);
                    mined = (parseFloat(mined) + (Math.random() * 0.05 + 0.01)).toFixed(4);
                    output.innerText = `Mined: ${mined} USDT`;
                    document.getElementById("status").innerText = "Mining complete!";
                    mining = false;
                }
            }, 150);
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return MINER_HTML

# --- Telegram Bot ---
async def start(update, context):
    await update.message.reply_text(
        "Welcome! The mini app is live here:\n👉 https://ton-usdt-miner-production.up.railway.app/"
    )

def setup_bot() -> Application:
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    return application

# --- Async Runner ---
async def main():
    application = setup_bot()
    asyncio.create_task(application.run_polling())
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
    )

if __name__ == "__main__":
    asyncio.run(main())
