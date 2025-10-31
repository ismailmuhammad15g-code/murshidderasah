#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سكريبت تفاعلي لإضافة المفاتيح المطلوبة إلى ملف .env
"""

import os
import sys

def read_env_file():
    """قراءة محتوى ملف .env الحالي"""
    env_path = '.env'
    if not os.path.exists(env_path):
        print("❌ خطأ: ملف .env غير موجود!")
        sys.exit(1)
    
    with open(env_path, 'r', encoding='utf-8') as f:
        return f.read()

def update_env_value(content, key, value):
    """تحديث قيمة مفتاح في محتوى .env"""
    lines = content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    
    return '\n'.join(lines), updated

def main():
    print("=" * 60)
    print("🔑 مساعد إعداد مفاتيح البوت")
    print("=" * 60)
    print()
    
    # قراءة ملف .env الحالي
    try:
        env_content = read_env_file()
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف .env: {e}")
        sys.exit(1)
    
    print("📋 سنقوم الآن بإضافة المفاتيح المطلوبة:")
    print()
    
    # 1. Google API Key
    print("1️⃣ Google API Key")
    print("-" * 60)
    print("🌐 احصل عليه من: https://aistudio.google.com")
    print("   1. سجل دخول بحسابك في Google")
    print("   2. اضغط 'Get API Key'")
    print("   3. انسخ المفتاح")
    print()
    google_key = input("📝 الصق مفتاح Google API هنا (أو اضغط Enter للتخطي): ").strip()
    
    if google_key:
        env_content, updated = update_env_value(env_content, "GOOGLE_API_KEY", google_key)
        if updated:
            print("✅ تم إضافة GOOGLE_API_KEY")
        else:
            print("⚠️ لم يتم العثور على GOOGLE_API_KEY في .env")
    else:
        print("⏭️ تم التخطي - يجب إضافته لاحقاً!")
    
    print()
    
    # 2. Telegram API ID
    print("2️⃣ Telegram API ID")
    print("-" * 60)
    print("🌐 احصل عليه من: https://my.telegram.org")
    print("   1. سجل دخول برقم هاتفك")
    print("   2. اضغط 'API development tools'")
    print("   3. أنشئ تطبيق جديد")
    print("   4. انسخ api_id")
    print()
    api_id = input("📝 الصق Telegram API ID هنا (أو اضغط Enter للتخطي): ").strip()
    
    if api_id:
        env_content, updated = update_env_value(env_content, "TELEGRAM_API_ID", api_id)
        if updated:
            print("✅ تم إضافة TELEGRAM_API_ID")
        else:
            print("⚠️ لم يتم العثور على TELEGRAM_API_ID في .env")
    else:
        print("⏭️ تم التخطي - يجب إضافته لاحقاً!")
    
    print()
    
    # 3. Telegram API Hash
    print("3️⃣ Telegram API Hash")
    print("-" * 60)
    print("🌐 من نفس الصفحة السابقة (my.telegram.org)")
    print("   انسخ api_hash")
    print()
    api_hash = input("📝 الصق Telegram API Hash هنا (أو اضغط Enter للتخطي): ").strip()
    
    if api_hash:
        env_content, updated = update_env_value(env_content, "TELEGRAM_API_HASH", api_hash)
        if updated:
            print("✅ تم إضافة TELEGRAM_API_HASH")
        else:
            print("⚠️ لم يتم العثور على TELEGRAM_API_HASH في .env")
    else:
        print("⏭️ تم التخطي - يجب إضافته لاحقاً!")
    
    print()
    
    # حفظ التغييرات
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        print("=" * 60)
        print("✅ تم حفظ التغييرات في ملف .env بنجاح!")
        print("=" * 60)
        print()
        
        # التحقق من المفاتيح
        missing = []
        if "GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY_HERE" in env_content:
            missing.append("GOOGLE_API_KEY")
        if "TELEGRAM_API_ID=YOUR_API_ID_HERE" in env_content:
            missing.append("TELEGRAM_API_ID")
        if "TELEGRAM_API_HASH=YOUR_API_HASH_HERE" in env_content:
            missing.append("TELEGRAM_API_HASH")
        
        if missing:
            print("⚠️ المفاتيح التالية لا تزال مطلوبة:")
            for key in missing:
                print(f"   ❌ {key}")
            print()
            print("💡 يمكنك:")
            print("   1. تشغيل هذا السكريبت مرة أخرى")
            print("   2. أو تعديل ملف .env يدوياً")
        else:
            print("🎉 رائع! جميع المفاتيح تم إضافتها!")
            print()
            print("📌 الخطوات التالية:")
            print("   1. شغّل: python main.py")
            print("   2. انتظر بناء قاعدة المعرفة (10-30 دقيقة)")
            print("   3. استمتع ببوتك الذكي! 🚀")
        
    except Exception as e:
        print(f"❌ خطأ في حفظ ملف .env: {e}")
        sys.exit(1)
    
    print()
    input("اضغط Enter للخروج...")

if __name__ == "__main__":
    main()
