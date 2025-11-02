import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_NAME = os.getenv("ADMIN_NAME")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

    # Webhook/Server Configuration
    WEBSITE_URL = os.getenv("WEBSITE_URL")  # مثال: https://yourusername.pythonanywhere.com
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # مثال: https://yourusername.pythonanywhere.com/webhook
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8080"))
    
    # Mail Configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")
    
    # Google AI Configuration
    # 🔥 دعم مفاتيح متعددة لزيادة السرعة
    _api_keys = []
    for i in range(1, 11):  # يدعم حتى 10 مفاتيح
        key = os.getenv(f"GOOGLE_API_KEY_{i}")
        if key and key != "YOUR_SECOND_KEY_HERE" and key != "YOUR_THIRD_KEY_HERE" and key != "YOUR_FOURTH_KEY_HERE" and key != "YOUR_FIFTH_KEY_HERE":
            _api_keys.append(key)
    
    # fallback للمفتاح القديم (GOOGLE_API_KEY)
    if not _api_keys:
        old_key = os.getenv("GOOGLE_API_KEY")
        if old_key:
            _api_keys.append(old_key)
    
    GOOGLE_API_KEYS = _api_keys if _api_keys else ["NO_API_KEY"]
    GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-pro-latest")
    GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "models/text-embedding-004")
    
    # Telethon Configuration
    TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
    
    # Channel Scraping Configuration (Legacy - للتوافق مع الكود القديم)
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "mahadalazhar")
    DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "365"))
    TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "3"))
    
    # === المصادر المتعددة (V2) ===
    # قائمة المصادر: القناة الرئيسية + جروب الإقامات
    # ملاحظة: يجب أن يكون الحساب (anon.session) منضماً للجروب الخاص
    TELEGRAM_SOURCES = [
        {
            "id": "mahadalazhar",  # القناة الرئيسية
            "tag": "public_channel",
            "type": "public"
        },
        {
            "id": os.getenv("ACCOMMODATIONS_GROUP_ID", ""),  # جروب الإقامات (يجب إضافته في .env)
            "tag": "accommodations",
            "type": "private"
        }
    ]
    
    # === الخطة البديلة: البحث في الويب ===
    # موقع قطاع المعاهد الأزهرية الرسمي
    AZHAR_WEBSITE_URL = os.getenv("AZHAR_WEBSITE_URL", "azhar.eg/education-sector")
    
    # Database Path
    DB_PATH = os.getenv("DB_PATH", "./db")
    
    # Flask App Configuration
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-flask")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///database.db")
