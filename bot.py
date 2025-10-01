import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import psycopg2

# ---------------- Database Setup ---------------- #
def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set!")
    return psycopg2.connect(database_url)

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
QUARTER_SECONDS = 3600*24*90  # approx 90 days
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
        # Update last_claim
        c.execute('UPDATE miners SET last_claim = %s WHERE user_id = %s AND miner_type = %s', (now, user_id, miner_type))
    
    conn.commit()
    conn.close()
    return total_usdt

# ---------------- Bot Commands ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)
    
    keyboard = [
        [InlineKeyboardButton("💰 Buy Miner", callback_data='buy_miner')],
        [InlineKeyboardButton("💵 Claim USDT Yield", callback_data='claim_yield')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 **TON Miner – Quarterly Yield Edition**\n\n"
        "Stake TON by buying miners.\n"
        "Each miner pays 4% quarterly yield in USDT based on TON price at purchase.\n"
        "Claim your USDT anytime!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        create_user(user.id, user.username or user.first_name)
        user_data = get_user(user.id)
    
    ton_balance = user_data[2]
    usdt_balance = user_data[3]
    
    # ---------------- Buy Miner ---------------- #
    if query.data == 'buy_miner':
        keyboard = [
            [InlineKeyboardButton("Small Miner (10 TON)", callback_data='miner_small')],
            [InlineKeyboardButton("Medium Miner (25 TON)", callback_data='miner_medium')],
            [InlineKeyboardButton("Large Miner (50 TON)", callback_data='miner_large')],
            [InlineKeyboardButton("XL Miner (100 TON)", callback_data='miner_xl')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("💰 **Buy Miners with TON**\nEarn 4% USDT per quarter.", reply_markup=reply_markup)
    
    elif query.data.startswith('miner_'):
        miner_type = query.data.split('_')[1]
        cost = MINER_COSTS[miner_type]
        current_ton_price = 2.75  # You can replace this with API fetch
        
        if ton_balance >= cost:
            update_user(user.id, ton_balance=ton_balance-cost)
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
        usdt_earned = calculate_quarterly_yield(user.id)
        if usdt_earned > 0:
            new_balance = usdt_balance + usdt_earned
            update_user(user.id, usdt_balance=new_balance, total_usdt_mined=user_data[4]+usdt_earned)
            await query.answer(f"✅ Claimed {usdt_earned:.2f} USDT from miners!", show_alert=True)
        else:
            await query.answer("❌ No yield available yet.", show_alert=True)
    
    # ---------------- Stats ---------------- #
    elif query.data == 'stats':
        # Calculate pending yield
        pending_usdt = calculate_quarterly_yield(user.id)
        display_balance = usdt_balance + pending_usdt
        
        keyboard = [[InlineKeyboardButton("💵 Claim USDT Yield", callback_data='claim_yield')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **Your Stats**\n\n"
            f"💰 TON Balance: {ton_balance:.6f}\n"
            f"💵 USDT Balance: {display_balance:.2f}\n"
            f"🏗 Total USDT Mined: {user_data[4]:.2f}",
            reply_markup=reply_markup
        )
    
    elif query.data == 'back':
        await start(update, context)

# ---------------- Admin Command ---------------- #
async def admin_add_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_ADMIN_ID:
        return
    try:
        amount = float(context.args[0])
        user_data = get_user(update.effective_user.id)
        new_balance = user_data[2] + amount
        update_user(update.effective_user.id, ton_balance=new_balance)
        await update.message.reply_text(f"✅ Added {amount} TON. New balance: {new_balance}")
    except:
        await update.message.reply_text("Usage: /adminton <amount>")

# ---------------- Main ---------------- #
def main():
    init_db()
    TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("adminton", admin_add_ton))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 TON Miner Bot started!")
    application.run_polling(allowed_updates=None)

if __name__ == '__main__':
    YOUR_ADMIN_ID = 8196865667  # Replace with your Telegram ID
    main()
