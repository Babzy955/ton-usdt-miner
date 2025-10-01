import os
import time
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import psycopg2

# ---------------- Load environment variables ---------------- #
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

if not TOKEN:
    raise Exception("BOT_TOKEN not found in environment variables!")
if not DATABASE_URL:
    raise Exception("DATABASE_URL not found in environment variables!")

# ---------------- Database Setup ---------------- #
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id BIGINT PRIMARY KEY,
                  username TEXT,
                  ton_balance REAL DEFAULT 0,
                  usdt_balance REAL DEFAULT 0,
                  total_usdt_mined REAL DEFAULT 0,
                  total_ton_invested REAL DEFAULT 0,
                  created_at REAL)''')
    
    # Miners table
    c.execute('''CREATE TABLE IF NOT EXISTS miners
                 (user_id BIGINT,
                  miner_type TEXT,
                  ton_invested REAL,
                  ton_price_at_purchase REAL,
                  start_time REAL,
                  last_claim REAL,
                  PRIMARY KEY (user_id, miner_type))''')
    
    conn.commit()
    conn.close()

# ---------------- Game Config ---------------- #
QUARTER_SECONDS = 3600*24*90  # ~90 days
MINER_YIELD = {
    'small': 0.04,
    'medium': 0.04,
    'large': 0.04,
    'xl': 0.04
}
MINER_COSTS = {
    'small': 10,
    'medium': 25,
    'large': 50,
    'xl': 100
}

# ---------------- User Management ---------------- #
def get_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def create_user(user_id, username):
    conn = get_db_connection()
    c = conn.cursor()
    now = time.time()
    c.execute('''INSERT INTO users (user_id, username, created_at)
                 VALUES (%s,%s,%s)
                 ON CONFLICT (user_id) DO NOTHING''', (user_id, username, now))
    conn.commit()
    conn.close()

def update_user(user_id, **kwargs):
    conn = get_db_connection()
    c = conn.cursor()
    for key, value in kwargs.items():
        c.execute(f'UPDATE users SET {key} = %s WHERE user_id = %s', (value, user_id))
    conn.commit()
    conn.close()

# ---------------- Yield Calculation ---------------- #
def calculate_quarterly_yield(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT miner_type, ton_invested, ton_price_at_purchase, last_claim FROM miners WHERE user_id = %s', (user_id,))
    miners = c.fetchall()
    total_usdt = 0
    now = time.time()
    
    for miner_type, ton_invested, ton_price, last_claim in miners:
        elapsed = now - (last_claim or now)
        quarters_passed = elapsed / QUARTER_SECONDS
        usdt_earned = ton_invested * ton_price * MINER_YIELD.get(miner_type,0) * quarters_passed
        total_usdt += usdt_earned
        c.execute('UPDATE miners SET last_claim = %s WHERE user_id = %s AND miner_type = %s', (now, user_id, miner_type))
    
    conn.commit()
    conn.close()
    return total_usdt

def calculate_min_withdrawal(user_id):
    user = get_user(user_id)
    if not user:
        return 0
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT ton_invested, ton_price_at_purchase FROM miners WHERE user_id = %s', (user_id,))
    miners = c.fetchall()
    conn.close()
    total_usd = sum(ton*price for ton,price in miners)
    return total_usd * 0.04

# ---------------- Bot Commands ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)
    
    keyboard = [
        [InlineKeyboardButton("💰 Buy Miner", callback_data='buy_miner')],
        [InlineKeyboardButton("💵 Claim USDT Yield", callback_data='claim_yield')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats')],
        [InlineKeyboardButton("ℹ️ Help/Info", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 **TON Miner – Quarterly USDT Yield**\n\n"
        "Stake TON by buying miners.\n"
        "Each miner pays 4% quarterly USDT yield based on TON price at purchase.\n"
        "Claim your USDT anytime when you reach minimum withdrawal.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)
    user_data = get_user(user.id)
    
    ton_balance = user_data[2]
    usdt_balance = user_data[3]
    
    # ---------------- Buy Miner ---------------- #
    if query.data == 'buy_miner':
        keyboard = [
            [InlineKeyboardButton(f"Small Miner – {MINER_COSTS['small']} TON", callback_data='miner_small')],
            [InlineKeyboardButton(f"Medium Miner – {MINER_COSTS['medium']} TON", callback_data='miner_medium')],
            [InlineKeyboardButton(f"Large Miner – {MINER_COSTS['large']} TON", callback_data='miner_large')],
            [InlineKeyboardButton(f"XL Miner – {MINER_COSTS['xl']} TON", callback_data='miner_xl')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💰 **Buy Miners** – 4% USDT quarterly yield", reply_markup=reply_markup)
    
    elif query.data.startswith('miner_'):
        miner_type = query.data.split('_')[1]
        cost = MINER_COSTS[miner_type]
        current_ton_price = 2.75  # replace with live API if desired
        
        if ton_balance >= cost:
            update_user(user.id, ton_balance=ton_balance-cost, total_ton_invested=user_data[5]+cost)
            now = time.time()
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''INSERT INTO miners (user_id, miner_type, ton_invested, ton_price_at_purchase, start_time, last_claim)
                         VALUES (%s,%s,%s,%s,%s,%s)
                         ON CONFLICT (user_id, miner_type)
                         DO UPDATE SET ton_invested = miners.ton_invested + EXCLUDED.ton_invested,
                                       ton_price_at_purchase = EXCLUDED.ton_price_at_purchase''',
                      (user.id, miner_type, cost, current_ton_price, now, now))
            conn.commit()
            conn.close()
            await query.answer(f"✅ Bought {miner_type.capitalize()} Miner for {cost} TON!", show_alert=True)
        else:
            await query.answer(f"❌ Not enough TON! You have {ton_balance}", show_alert=True)
    
    # ---------------- Claim Yield ---------------- #
    elif query.data == 'claim_yield':
        pending_usdt = calculate_quarterly_yield(user.id)
        min_withdraw = calculate_min_withdrawal(user.id)
        if pending_usdt >= min_withdraw:
            new_balance = usdt_balance + pending_usdt
            update_user(user.id, usdt_balance=new_balance, total_usdt_mined=user_data[4]+pending_usdt)
            await query.answer(f"✅ Claimed {pending_usdt:.2f} USDT!", show_alert=True)
        else:
            await query.answer(f"❌ Minimum withdraw is {min_withdraw:.2f} USDT. Pending yield: {pending_usdt:.2f} USDT", show_alert=True)
    
    # ---------------- Stats ---------------- #
    elif query.data == 'stats':
        pending_usdt = calculate_quarterly_yield(user.id)
        keyboard = [
            [InlineKeyboardButton("💵 Claim USDT Yield", callback_data='claim_yield')],
            [InlineKeyboardButton("💰 Buy Miner", callback_data='buy_miner')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📊 **Your Stats**\n\n"
            f"💰 TON Balance: {ton_balance:.6f}\n"
            f"💵 USDT Balance: {usdt_balance:.2f} (Pending: {pending_usdt:.2f})\n"
            f"🏗 Total USDT Mined: {user_data[4]:.2f}",
            reply_markup=reply_markup
        )
    
    elif query.data == 'help':
        await query.edit_message_text(
            "ℹ️ **How it works**\n\n"
            "• Buy miners with TON.\n"
            "• Each miner pays 4% quarterly USDT based on TON price at purchase.\n"
            "• Claim USDT once pending yield reaches minimum withdrawal.\n"
            "• Stats show your balances and pending yield.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data='back')]])
        )
    
    elif query.data == 'back':
        await start_from_callback(update, context)

async def start_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await start(update, context)

# ---------------- Main ---------------- #
def main():
    init_db()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 TON Miner Bot running...")
    application.run_polling()

if __name__ == '__main__':
    main()
