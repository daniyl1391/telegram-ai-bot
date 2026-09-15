from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.database import db
from bot.services.subscription import subscription_manager

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "user", user.first_name)
    
    sub = db.get_subscription(user.id)
    if not sub:
        subscription_manager.create_free(user.id)
    
    keyboard = [
        [InlineKeyboardButton("AI Chat", callback_data="ai_chat")],
        [InlineKeyboardButton("Shop", callback_data="shop")],
        [InlineKeyboardButton("Buy Plan", callback_data="buy_subscription")],
        [InlineKeyboardButton("Support", callback_data="support")],
        [InlineKeyboardButton("My Account", callback_data="account")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"Hello {user.first_name}! Welcome to AI Bot.\n\nSelect an option:"
    
    await update.message.reply_text(text, reply_markup=reply_markup)

async def account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sub = db.get_subscription(user_id)
    
    if not sub:
        text = "Error: Account not found"
    else:
        remaining = sub["message_limit"] - sub["message_used"]
        expire = sub["expire_date"]
        text = f"Account: {sub['plan']}\nMessages left: {remaining}/{sub['message_limit']}\nExpires: {expire}"
    
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text)
