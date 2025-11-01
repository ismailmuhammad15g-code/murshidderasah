#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# run_both.py
"""
سكريبت لتشغيل البوت والموقع معاً في نفس الترمينال
"""

import os
import sys
import threading
import time
import io

# إصلاح مشكلة الترميز في Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def print_banner():
    """طباعة لافتة البداية"""
    print("=" * 60)
    print("تشغيل البوت والموقع معا")
    print("=" * 60)
    print()
    print("جاري تشغيل التطبيقات...")
    print("البوت: Telegram Bot (polling)")
    print("الموقع: http://localhost:8080")
    print("الحساب التجريبي: admin / admin123")
    print()
    print("اضغط Ctrl+C للإيقاف")
    print()
    print("=" * 60)
    print()

def run_telegram_bot():
    """تشغيل بوت التليجرام (من main.py الأصلي)"""
    import subprocess
    subprocess.run([sys.executable, "main.py"])

def run_flask_website():
    """تشغيل موقع Flask"""
    # انتظر قليلاً لبدء البوت أولاً
    time.sleep(3)
    
    from flask_app import app, setup_telegram_bot
    from config import Config
    
    print("✅ جاري تشغيل الموقع...")
    
    # لا نقوم بإعداد البوت هنا لأنه يعمل بالفعل في main.py
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=False,
        use_reloader=False
    )

def main():
    """الدالة الرئيسية"""
    
    # التحقق من .env
    if not os.path.exists('.env'):
        print("❌ ملف .env غير موجود!")
        print("💡 يرجى إنشاء ملف .env وإضافة المفاتيح المطلوبة")
        sys.exit(1)
    
    # طباعة اللافتة
    print_banner()
    
    # تشغيل الموقع في thread منفصل
    flask_thread = threading.Thread(target=run_flask_website, daemon=True)
    flask_thread.start()
    
    # تشغيل البوت في thread الرئيسي
    try:
        run_telegram_bot()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("تم إيقاف التطبيقات. شكرا لاستخدامك!")
        print("=" * 60)
        sys.exit(0)

if __name__ == '__main__':
    main()
