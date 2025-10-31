#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
سكريبت لاختبار سحب الرسائل فقط (بدون بناء قاعدة البيانات)
يفيد لمعرفة كم رسالة سيتم سحبها قبل بدء البناء الكامل
"""

import asyncio
import logging
import scraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scraping():
    """اختبار سحب الرسائل"""
    
    print("="*60)
    print("🧪 اختبار سحب الرسائل من القناة")
    print("="*60)
    print()
    
    logger.info("📥 بدء سحب الرسائل...")
    documents = await scraper.scrape_channel()
    
    if documents is None:
        print()
        print("❌ فشل السحب!")
        print()
        print("💡 الحلول المحتملة:")
        print("  1. تأكد من صحة TELEGRAM_API_ID و TELEGRAM_API_HASH في ملف .env")
        print("  2. تأكد من أن حسابك منضم لقناة @mahadalazhar")
        print("  3. حاول حذف ملف 'anon.session' وإعادة المحاولة")
        return
    
    print()
    print("="*60)
    print(f"✅ تم سحب {len(documents)} رسالة بنجاح!")
    print("="*60)
    print()
    
    if len(documents) > 0:
        print("📋 عينة من أول 3 رسائل:")
        print()
        for i, doc in enumerate(documents[:3], 1):
            print(f"{i}. {doc['text'][:80]}...")
            print(f"   🔗 {doc['link']}")
            print()
        
        print("="*60)
        print("📊 الإحصائيات:")
        print(f"  - إجمالي الرسائل: {len(documents)}")
        print(f"  - الوقت التقديري للبناء: {(len(documents) // 40) * 65 / 60:.1f} دقيقة")
        print("="*60)
        print()
        print("💡 لبناء قاعدة البيانات الكاملة، شغّل:")
        print("   python rebuild_database.py")
    else:
        print("⚠️ لم يتم سحب أي رسائل!")
        print()
        print("💡 السبب المحتمل:")
        print("  - حسابك غير منضم للقناة @mahadalazhar")
        print("  - أو لا توجد رسائل في الفترة المحددة (365 يوم)")

if __name__ == "__main__":
    asyncio.run(test_scraping())
