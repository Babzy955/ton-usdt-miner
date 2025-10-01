import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = "8235411673:AAGJBuKA0Y2PIGr06f12onmdRNX472123kc"

GAME_CONFIG = {
    'miner_price_ton': 10,
    'quarterly_return': 0.03,
    'start_usdt': 0.00000001,
    'update_interval': 60
}

USERS = {}

def create_user(user_id, username):
    if user_id not in USERS:
        USERS[user_id] = {
            "username": username,
            "ton_invested": 0,
            "miner_usdt": GAME_CONFIG['start_usdt'],
            "miner_start_time": time.time()
        }

def update_miner(user_id):
    user = USERS[user_id]
    elapsed_seconds = time.time() - user['miner_start_time']
    total_quarter_seconds = 90 * 24 * 3600
    quarters_elapsed = elapsed_seconds / total_quarter_seconds
    user['miner_usdt'] = GAME_CONFIG['start_usdt'] * ((1 + GAME_CONFIG['quarterly_return']) ** quarters_elapsed)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)

    keyboard = [
        [InlineKeyboardButton("💰 Open Miner App", web_app=WebAppInfo(url="https://example.com/miner.html"))],
        [InlineKeyboardButton("📊 Stats", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎮 Welcome {user.username}! Your miner is ready. Click below to view your balance and info.",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    create_user(user_id, query.from_user.username or query.from_user.first_name)
    update_miner(user_id)
    user = USERS[user_id]

    if query.data == 'stats':
        await query.edit_message_text(
            f"📊 **Miner Stats**\n\n"
            f"TON Invested: {user['ton_invested']}\n"
            f"USDT Mined: {user['miner_usdt']:.8f}\n"
            f"Miner pays x USDT every 3 months (continuous mining)\n",
            parse_mode='Markdown'
        )

async def miner_loop():
    while True:
        for user_id in USERS:
            update_miner(user_id)
        await asyncio.sleep(GAME_CONFIG['update_interval'])

# This will run after the bot is fully initialized
async def on_startup(application: Application):
    application.create_task(miner_loop())

def main():
    application = Application.builder().token(BOT_TOKEN).post_init(on_startup).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Bot started!")
    application.run_polling()

if __name__ == "__main__":
    main()
