#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
بناء سريع لقاعدة البيانات مع تتبع التقدم
"""

import asyncio
import logging
import time
from datetime import datetime
import scraper
import vector_store
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def quick_build():
    print("="*70)
    print("🚀 بناء قاعدة البيانات السريع")
    print("="*70)
    print()
    
    # عرض معلومات المفاتيح
    num_keys = len(Config.GOOGLE_API_KEYS)
    print(f"🔥 المفاتيح المحملة: {num_keys} مفتاح")
    print(f"⚡ السرعة المتوقعة: {num_keys}x")
    
    if num_keys == 1:
        estimated_time = 4.5 * 60  # دقائق
    else:
        estimated_time = (4.5 * 60) / num_keys
    
    print(f"⏱️  الوقت المتوقع: ~{int(estimated_time)} دقيقة")
    print()
    print("="*70)
    
    # بدء العد
    start_time = time.time()
    
    # سحب الرسائل
    print()
    print("📥 الخطوة 1/2: سحب الرسائل من القناة...")
    print("-" * 70)
    documents = await scraper.scrape_channel()
    
    if documents is None:
        print()
        print("❌ فشل سحب الرسائل!")
        print("💡 تأكد من:")
        print("   1. صحة TELEGRAM_API_ID و TELEGRAM_API_HASH")
        print("   2. حسابك منضم لقناة @mahadalazhar")
        return False
    
    if len(documents) == 0:
        print()
        print("⚠️ تم سحب 0 رسالة!")
        print("💡 حاول حذف ملف 'anon.session' وأعد المحاولة")
        return False
    
    print()
    print(f"✅ تم سحب {len(documents)} رسالة بنجاح!")
    print()
    
    # بناء قاعدة البيانات
    print("🏗️  الخطوة 2/2: بناء قاعدة المتجهات...")
    print("-" * 70)
    print(f"📊 سيتم معالجة {len(documents)} رسالة")
    print(f"🔄 عدد الدفعات: {(len(documents) + 39) // 40}")
    print(f"⚡ استخدام {num_keys} مفتاح بالتوازي")
    print()
    
    vector_store.build_database(documents)
    
    # الانتهاء
    elapsed_time = time.time() - start_time
    elapsed_minutes = int(elapsed_time / 60)
    elapsed_seconds = int(elapsed_time % 60)
    
    print()
    print("="*70)
    print("🎉 اكتمل بناء قاعدة البيانات!")
    print("="*70)
    print(f"✅ تم معالجة: {len(documents)} رسالة")
    print(f"⏱️  الوقت الفعلي: {elapsed_minutes} دقيقة و {elapsed_seconds} ثانية")
    print(f"🔥 السرعة: {num_keys}x باستخدام {num_keys} مفتاح")
    print()
    print("🚀 البوت جاهز الآن!")
    print("▶️  شغّل البوت: python main.py")
    print("="*70)
    
    return True

if __name__ == "__main__":
    print()
    print("⚡ بدء البناء السريع...")
    print()
    
    success = asyncio.run(quick_build())
    
    if not success:
        print()
        print("="*70)
        print("❌ فشلت العملية")
        print("="*70)
