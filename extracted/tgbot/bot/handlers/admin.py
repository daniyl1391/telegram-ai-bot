from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.config import ADMIN_USER_IDS
from bot.database import db

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("Unauthorized")
        return
    
    keyboard = [
        [InlineKeyboardButton("Users", callback_data="admin_users")],
        [InlineKeyboardButton("Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("AI Models", callback_data="admin_ai")],
        [InlineKeyboardButton("Products", callback_data="admin_products")],
        [InlineKeyboardButton("Payment", callback_data="admin_payment")],
        [InlineKeyboardButton("Tickets", callback_data="admin_tickets")],
        [InlineKeyboardButton("Settings", callback_data="admin_settings")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Admin Panel", reply_markup=reply_markup)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        return
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM products")
    product_count = cursor.fetchone()["count"]
    
    cursor.execute("SELECT COUNT(*) as count FROM payments WHERE status = 'confirmed'")
    payment_count = cursor.fetchone()["count"]
    
    conn.close()
    
    text = f"Stats:\nUsers: {user_count}\nProducts: {product_count}\nPayments: {payment_count}"
    
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text)
