import os
import time
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Database setup
def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set!")
    return psycopg2.connect(database_url)

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id BIGINT PRIMARY KEY,
                  username TEXT,
                  ton_balance REAL DEFAULT 0,
                  gems INTEGER DEFAULT 0,
                  pickaxe_level INTEGER DEFAULT 1,
                  workers INTEGER DEFAULT 0,
                  mining_rig_level INTEGER DEFAULT 0,
                  last_claim REAL,
                  wallet_address TEXT,
                  total_mined REAL DEFAULT 0,
                  created_at REAL)''')
    conn.commit()
    conn.close()

# Game configuration
GAME_CONFIG = {
    'tap_reward': 0.001,  # TON per tap
    'pickaxe_costs': [10, 25, 50, 100, 200, 500],  # Gems cost for each level
    'pickaxe_multipliers': [1, 1.5, 2, 3, 5, 8],
    'worker_cost': 50,  # Gems per worker
    'worker_rate': 0.0001,  # TON per hour per worker
    'rig_costs': [100, 250, 500, 1000],
    'rig_multipliers': [1, 2, 4, 8],
    'gem_to_ton': 0.01,  # 1 gem = 0.01 TON when buying gems
}

# User management
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
    c.execute('''INSERT INTO users 
                 (user_id, username, last_claim, created_at) 
                 VALUES (%s, %s, %s, %s)
                 ON CONFLICT (user_id) DO NOTHING''', (user_id, username, now, now))
    conn.commit()
    conn.close()

def update_user(user_id, **kwargs):
    conn = get_db_connection()
    c = conn.cursor()
    for key, value in kwargs.items():
        c.execute(f'UPDATE users SET {key} = %s WHERE user_id = %s', (value, user_id))
    conn.commit()
    conn.close()

def calculate_passive_income(user):
    if not user:
        return 0
    
    user_id, username, ton_balance, gems, pickaxe, workers, rig, last_claim, wallet, total_mined, created = user
    
    hours_passed = (time.time() - last_claim) / 3600
    hours_passed = min(hours_passed, 24)  # Cap at 24 hours
    
    worker_income = workers * GAME_CONFIG['worker_rate'] * hours_passed
    rig_multiplier = GAME_CONFIG['rig_multipliers'][min(rig, len(GAME_CONFIG['rig_multipliers'])-1)]
    
    total_income = worker_income * rig_multiplier
    return total_income

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_user(user.id, user.username or user.first_name)
    
    user_data = get_user(user.id)
    passive = calculate_passive_income(user_data)
    
    if passive > 0:
        new_balance = user_data[2] + passive
        update_user(user.id, ton_balance=new_balance, last_claim=time.time())
    
    keyboard = [
        [InlineKeyboardButton("⛏️ Mine", callback_data='mine')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats'),
         InlineKeyboardButton("🏪 Shop", callback_data='shop')],
        [InlineKeyboardButton("💎 Buy Gems", callback_data='buy_gems'),
         InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("👛 Connect Wallet", callback_data='connect_wallet')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = f"""
🎮 **Welcome to TON Miner!** ⛏️

Start mining TON by tapping the Mine button!
Upgrade your equipment to mine faster.
Hire workers for passive income!

{"💰 You earned " + f"{passive:.6f}" + " TON while you were away!" if passive > 0 else ""}

Tap a button to begin your mining journey!
"""
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        create_user(user.id, user.username or user.first_name)
        user_data = get_user(user.id)
    
    user_id, username, ton_balance, gems, pickaxe, workers, rig, last_claim, wallet, total_mined, created = user_data
    
    if query.data == 'mine':
        pickaxe_mult = GAME_CONFIG['pickaxe_multipliers'][min(pickaxe-1, len(GAME_CONFIG['pickaxe_multipliers'])-1)]
        reward = GAME_CONFIG['tap_reward'] * pickaxe_mult
        
        new_balance = ton_balance + reward
        new_total = total_mined + reward
        update_user(user.id, ton_balance=new_balance, total_mined=new_total)
        
        keyboard = [
            [InlineKeyboardButton("⛏️ Mine Again!", callback_data='mine')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⛏️ **You mined {reward:.6f} TON!**\n\n"
            f"💰 Balance: {new_balance:.6f} TON\n"
            f"⚒️ Pickaxe Level: {pickaxe} ({pickaxe_mult}x)\n\n"
            f"Keep tapping to mine more!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'stats':
        passive = calculate_passive_income(user_data)
        if passive > 0:
            ton_balance += passive
            update_user(user.id, ton_balance=ton_balance, last_claim=time.time())
        
        worker_per_hour = workers * GAME_CONFIG['worker_rate']
        rig_mult = GAME_CONFIG['rig_multipliers'][min(rig, len(GAME_CONFIG['rig_multipliers'])-1)]
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **Your Mining Stats**\n\n"
            f"💰 Balance: {ton_balance:.6f} TON\n"
            f"💎 Gems: {gems}\n"
            f"⚒️ Pickaxe Level: {pickaxe}\n"
            f"👷 Workers: {workers}\n"
            f"🏭 Mining Rig Level: {rig}\n"
            f"⚡ Passive Income: {worker_per_hour * rig_mult:.6f} TON/hour\n"
            f"📈 Total Mined: {total_mined:.6f} TON\n"
            f"👛 Wallet: {wallet if wallet else 'Not connected'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'shop':
        keyboard = [
            [InlineKeyboardButton("⚒️ Upgrade Pickaxe", callback_data='shop_pickaxe')],
            [InlineKeyboardButton("👷 Hire Worker", callback_data='shop_worker')],
            [InlineKeyboardButton("🏭 Upgrade Mining Rig", callback_data='shop_rig')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🏪 **Mining Shop**\n\n"
            "Choose what you'd like to upgrade:\n\n"
            "⚒️ **Pickaxe** - Increases mining per tap\n"
            "👷 **Workers** - Earn passive income\n"
            "🏭 **Mining Rig** - Multiplies worker income",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'shop_pickaxe':
        next_level = pickaxe
        if next_level >= len(GAME_CONFIG['pickaxe_costs']):
            cost = "MAX LEVEL"
            next_mult = GAME_CONFIG['pickaxe_multipliers'][-1]
        else:
            cost = f"{GAME_CONFIG['pickaxe_costs'][next_level]} gems"
            next_mult = GAME_CONFIG['pickaxe_multipliers'][next_level]
        
        keyboard = []
        if pickaxe < len(GAME_CONFIG['pickaxe_costs']):
            keyboard.append([InlineKeyboardButton(f"⬆️ Upgrade ({cost})", callback_data='buy_pickaxe')])
        keyboard.append([InlineKeyboardButton("🔙 Back to Shop", callback_data='shop')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        current_mult = GAME_CONFIG['pickaxe_multipliers'][pickaxe-1]
        
        await query.edit_message_text(
            f"⚒️ **Pickaxe Upgrade**\n\n"
            f"Current Level: {pickaxe} ({current_mult}x multiplier)\n"
            f"Next Level: {pickaxe+1} ({next_mult}x multiplier)\n"
            f"Cost: {cost}\n\n"
            f"Your gems: {gems}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'buy_pickaxe':
        if pickaxe >= len(GAME_CONFIG['pickaxe_costs']):
            await query.answer("Already at max level!", show_alert=True)
            return
        
        cost = GAME_CONFIG['pickaxe_costs'][pickaxe]
        if gems >= cost:
            update_user(user.id, gems=gems-cost, pickaxe_level=pickaxe+1)
            await query.answer(f"✅ Pickaxe upgraded to level {pickaxe+1}!", show_alert=True)
            await button_handler(update, context)  # Refresh
        else:
            await query.answer(f"❌ Not enough gems! Need {cost}, have {gems}", show_alert=True)
    
    elif query.data == 'shop_worker':
        keyboard = [
            [InlineKeyboardButton(f"👷 Hire Worker ({GAME_CONFIG['worker_cost']} gems)", callback_data='buy_worker')],
            [InlineKeyboardButton("🔙 Back to Shop", callback_data='shop')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        income_per_worker = GAME_CONFIG['worker_rate']
        
        await query.edit_message_text(
            f"👷 **Hire Workers**\n\n"
            f"Current Workers: {workers}\n"
            f"Income per worker: {income_per_worker:.6f} TON/hour\n"
            f"Cost: {GAME_CONFIG['worker_cost']} gems each\n\n"
            f"Your gems: {gems}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'buy_worker':
        cost = GAME_CONFIG['worker_cost']
        if gems >= cost:
            update_user(user.id, gems=gems-cost, workers=workers+1)
            await query.answer(f"✅ Worker hired! Now you have {workers+1} workers", show_alert=True)
            await button_handler(update, context)
        else:
            await query.answer(f"❌ Not enough gems! Need {cost}, have {gems}", show_alert=True)
    
    elif query.data == 'shop_rig':
        if rig >= len(GAME_CONFIG['rig_costs']):
            cost = "MAX LEVEL"
            next_mult = GAME_CONFIG['rig_multipliers'][-1]
        else:
            cost = f"{GAME_CONFIG['rig_costs'][rig]} gems"
            next_mult = GAME_CONFIG['rig_multipliers'][rig]
        
        keyboard = []
        if rig < len(GAME_CONFIG['rig_costs']):
            keyboard.append([InlineKeyboardButton(f"⬆️ Upgrade ({cost})", callback_data='buy_rig')])
        keyboard.append([InlineKeyboardButton("🔙 Back to Shop", callback_data='shop')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        current_mult = GAME_CONFIG['rig_multipliers'][rig] if rig > 0 else 1
        
        await query.edit_message_text(
            f"🏭 **Mining Rig Upgrade**\n\n"
            f"Current Level: {rig} ({current_mult}x multiplier)\n"
            f"Next Level: {rig+1} ({next_mult}x multiplier)\n"
            f"Cost: {cost}\n\n"
            f"Rigs multiply your worker income!\n"
            f"Your gems: {gems}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'buy_rig':
        if rig >= len(GAME_CONFIG['rig_costs']):
            await query.answer("Already at max level!", show_alert=True)
            return
        
        cost = GAME_CONFIG['rig_costs'][rig]
        if gems >= cost:
            update_user(user.id, gems=gems-cost, mining_rig_level=rig+1)
            await query.answer(f"✅ Mining rig upgraded to level {rig+1}!", show_alert=True)
            await button_handler(update, context)
        else:
            await query.answer(f"❌ Not enough gems! Need {cost}, have {gems}", show_alert=True)
    
    elif query.data == 'buy_gems':
        keyboard = [
            [InlineKeyboardButton("💎 100 gems (1 TON)", callback_data='gems_100')],
            [InlineKeyboardButton("💎 500 gems (4.5 TON)", callback_data='gems_500')],
            [InlineKeyboardButton("💎 1000 gems (8 TON)", callback_data='gems_1000')],
            [InlineKeyboardButton("🔙 Back", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "💎 **Buy Gems with TON**\n\n"
            "Gems are used to purchase upgrades!\n"
            "Select a package:\n\n"
            "Note: Wallet integration coming soon!\n"
            "For now, this is just a demo.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('gems_'):
        await query.answer("💎 Wallet payment integration coming soon! This is a demo version.", show_alert=True)
    
    elif query.data == 'connect_wallet':
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "👛 **Connect TON Wallet**\n\n"
            "Wallet integration is coming soon!\n\n"
            "You'll be able to:\n"
            "• Buy gems with TON\n"
            "• Withdraw your mined TON\n"
            "• Secure your account\n\n"
            "For now, enjoy the free demo version!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif query.data == 'leaderboard':
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT username, total_mined FROM users ORDER BY total_mined DESC LIMIT 10')
        top_users = c.fetchall()
        conn.close()
        
        leaderboard_text = "🏆 **Top Miners**\n\n"
        for idx, (name, mined) in enumerate(top_users, 1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            leaderboard_text += f"{medal} {name}: {mined:.6f} TON\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(leaderboard_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == 'back':
        await start_from_callback(update, context)

async def start_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    user_data = get_user(user.id)
    
    passive = calculate_passive_income(user_data)
    if passive > 0:
        new_balance = user_data[2] + passive
        update_user(user.id, ton_balance=new_balance, last_claim=time.time())
    
    keyboard = [
        [InlineKeyboardButton("⛏️ Mine", callback_data='mine')],
        [InlineKeyboardButton("📊 Stats", callback_data='stats'),
         InlineKeyboardButton("🏪 Shop", callback_data='shop')],
        [InlineKeyboardButton("💎 Buy Gems", callback_data='buy_gems'),
         InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
        [InlineKeyboardButton("👛 Connect Wallet", callback_data='connect_wallet')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = f"""
🎮 **TON Miner** ⛏️

Start mining TON by tapping the Mine button!
Upgrade your equipment to mine faster.
Hire workers for passive income!

{"💰 You earned " + f"{passive:.6f}" + " TON while you were away!" if passive > 0 else ""}
"""
    
    await query.edit_message_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')

# Admin command to give gems (for testing)
async def admin_gems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != YOUR_ADMIN_ID:  # Replace with your Telegram ID
        return
    
    try:
        amount = int(context.args[0])
        update_user(update.effective_user.id, gems=amount)
        await update.message.reply_text(f"✅ Set gems to {amount}")
    except:
        await update.message.reply_text("Usage: /admingems <amount>")

def main():
    # Initialize database
    init_db()
    
    # Your bot token
    TOKEN = os.getenv('BOT_TOKEN', '8309297935:AAFev_cuH-HUUe_XxIaKdWpXqgiB56OPQqg')
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admingems", admin_gems))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    YOUR_ADMIN_ID = 8196865667  # Replace with your Telegram user ID
    main()