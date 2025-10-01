import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# -------------------------
# BOT CONFIG
# -------------------------
BOT_TOKEN = "8309297935:AAFev_cuH-HUUe_XxIaKdWpXqgiB56OPQqg"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -------------------------
# COMMAND HANDLERS
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the TON Interest Bot!\n\nUse /help to see all commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Available commands:\n"
        "/start - Begin using the bot\n"
        "/help - Show this help menu\n"
        "/invest - Invest TON\n"
        "/balance - Check your balance\n"
        "/withdraw - Withdraw funds"
    )

async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💰 To invest, please send your TON wallet address and amount.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Your balance is: 0 TON (demo).")

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏦 Minimum withdrawal is equal to your invested amount.\nPlease provide your TON wallet address to continue.")

# -------------------------
# MAIN
# -------------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("invest", invest))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("withdraw", withdraw))

    logging.info("🚀 Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
