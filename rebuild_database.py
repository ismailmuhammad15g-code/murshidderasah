#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لإعادة بناء قاعدة البيانات من الصفر
سيحذف قاعدة البيانات القديمة ويسحب كل الرسائل من جديد
"""

import os
import asyncio
import logging
import scraper
import vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def rebuild():
    """حذف قاعدة البيانات القديمة وإعادة البناء"""
    
    db_path = "db/lite_store.json"
    
    # حذف القاعدة القديمة
    if os.path.exists(db_path):
        logger.info("🗑️ حذف قاعدة البيانات القديمة...")
        os.remove(db_path)
        logger.info("✅ تم الحذف")
    
    # سحب الرسائل
    logger.info("📥 بدء سحب الرسائل من القناة...")
    documents = await scraper.scrape_channel()
    
    if documents is None:
        logger.error("❌ فشل سحب الرسائل! تأكد من:")
        logger.error("  1. مفاتيح TELEGRAM_API_ID و TELEGRAM_API_HASH صحيحة")
        logger.error("  2. حسابك منضم لقناة @mahadalazhar")
        return False
    
    if len(documents) == 0:
        logger.error("❌ تم سحب 0 رسالة!")
        logger.error("  حل: احذف ملف 'anon.session' وحاول مرة أخرى")
        return False
    
    logger.info(f"✅ تم سحب {len(documents)} رسالة")
    
    # بناء قاعدة البيانات
    logger.info("🏗️ بدء بناء قاعدة البيانات...")
    logger.info("⚠️ هذا قد يستغرق ساعات (40 رسالة كل 65 ثانية)")
    logger.info("⚠️ لا تغلق البرنامج!")
    
    vector_store.build_database(documents)
    
    logger.info("🎉 اكتمل بناء قاعدة البيانات!")
    logger.info(f"📊 تم معالجة {len(documents)} رسالة")
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("🔄 إعادة بناء قاعدة البيانات")
    print("="*60)
    print()
    print("⚠️ تحذير: سيتم حذف قاعدة البيانات الحالية!")
    print()
    
    confirm = input("هل تريد المتابعة؟ (yes/no): ")
    
    if confirm.lower() in ['yes', 'y', 'نعم']:
        print()
        print("🚀 بدء العملية...")
        print()
        
        success = asyncio.run(rebuild())
        
        if success:
            print()
            print("="*60)
            print("✅ تم بنجاح! البوت جاهز للاستخدام")
            print("="*60)
        else:
            print()
            print("="*60)
            print("❌ فشلت العملية! راجع الأخطاء أعلاه")
            print("="*60)
    else:
        print("تم الإلغاء.")
