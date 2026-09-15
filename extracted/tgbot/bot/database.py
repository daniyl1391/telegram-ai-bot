import sqlite3, logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self.init_db()
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
            is_admin BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            plan TEXT DEFAULT 'free', message_limit INTEGER DEFAULT 10,
            message_used INTEGER DEFAULT 0, expire_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS ai_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
            api_url TEXT, api_key TEXT, model_name TEXT, status BOOLEAN DEFAULT 1,
            is_default BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            description TEXT, price INTEGER, duration_days INTEGER,
            product_type TEXT, messages_count INTEGER, status BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            product_id INTEGER, amount INTEGER, payment_method TEXT,
            status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            subject TEXT, status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER NOT NULL,
            user_id INTEGER, message TEXT, is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE NOT NULL,
            value TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username, first_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)",
                         (user_id, username, first_name))
            conn.commit()
        finally:
            conn.close()
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None
    
    def get_subscription(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
        sub = cursor.fetchone()
        conn.close()
        return dict(sub) if sub else None
    
    def create_subscription(self, user_id, plan, message_limit, duration_days=30):
        conn = self.get_connection()
        cursor = conn.cursor()
        expire_date = datetime.now() + timedelta(days=duration_days)
        try:
            cursor.execute("INSERT INTO subscriptions (user_id, plan, message_limit, expire_date) VALUES (?, ?, ?, ?)",
                         (user_id, plan, message_limit, expire_date))
            conn.commit()
        finally:
            conn.close()
    
    def add_ai_model(self, name, api_url, api_key, model_name):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO ai_models (name, api_url, api_key, model_name, status) VALUES (?, ?, ?, ?, 1)",
                         (name, api_url, api_key, model_name))
            conn.commit()
        finally:
            conn.close()
    
    def get_ai_models(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ai_models WHERE status = 1")
        models = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return models
    
    def get_setting(self, key):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def set_setting(self, key, value):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        finally:
            conn.close()
    
    def create_product(self, name, description, price, duration_days, product_type, messages_count=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO products (name, description, price, duration_days, product_type, messages_count) VALUES (?, ?, ?, ?, ?, ?)",
                         (name, description, price, duration_days, product_type, messages_count))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_products(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE status = 1")
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return products

db = Database("bot.db")
