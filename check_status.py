#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""سكريبت فحص حالة البوت والموقع"""

import requests
import time

print("=" * 70)
print("🔍 فحص حالة البوت والموقع")
print("=" * 70)
print()

# فحص Flask App
print("1️⃣ فحص Flask App (المنفذ 5000)...")
try:
    response = requests.get("http://localhost:5000", timeout=5)
    if response.status_code == 200:
        print("   ✅ Flask App يعمل بنجاح!")
    else:
        print(f"   ⚠️ Flask App يستجيب بكود: {response.status_code}")
except requests.exceptions.ConnectionRefusedError:
    print("   ❌ Flask App غير متصل (المنفذ 5000 مغلق)")
except Exception as e:
    print(f"   ❌ خطأ: {e}")

print()

# فحص قاعدة البيانات
print("2️⃣ فحص قاعدة البيانات...")
import os
if os.path.exists("db"):
    db_files = os.listdir("db")
    if db_files:
        print(f"   ✅ قاعدة البيانات موجودة ({len(db_files)} ملف)")
    else:
        print("   ⚠️ مجلد قاعدة البيانات فارغ")
else:
    print("   ❌ مجلد قاعدة البيانات غير موجود")

print()

# فحص ملف .env
print("3️⃣ فحص الإعدادات...")
if os.path.exists(".env"):
    print("   ✅ ملف .env موجود")
    
    # قراءة عدد المفاتيح
    from config import Config
    num_keys = len(Config.GOOGLE_API_KEYS)
    print(f"   📊 عدد مفاتيح Google API: {num_keys}")
    
    if Config.BOT_TOKEN and Config.BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
        print("   ✅ Bot Token مُعرّف")
    else:
        print("   ❌ Bot Token غير مُعرّف")
else:
    print("   ❌ ملف .env غير موجود")

print()
print("=" * 70)
print("✅ انتهى الفحص")
print("=" * 70)
