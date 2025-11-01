"""
===================================
daily_update.py - التحديث اليومي التلقائي
===================================

هذا السكريبت يتم تشغيله يومياً على PythonAnywhere
يقوم بسحب الرسائل الجديدة وتحديث قاعدة البيانات

الاستخدام على PythonAnywhere:
    - اذهب إلى Tasks
    - أنشئ مهمة يومية جديدة
    - الأمر: python daily_update.py
    - الوقت: اختر وقتاً مناسباً (مثلاً 3:00 صباحاً)
"""

import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_update.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def scrape_new_messages():
    """سحب الرسائل الجديدة من القناة"""
    try:
        logger.info("🔍 بدء سحب الرسائل الجديدة...")
        
        from scraper import scrape_all_sources
        
        # سحب الرسائل من آخر 7 أيام فقط (لتوفير الوقت)
        messages = await scrape_all_sources(days_limit=7)
        
        if messages:
            logger.info(f"✅ تم سحب {len(messages)} رسالة جديدة")
            return messages
        else:
            logger.info("ℹ️ لم يتم العثور على رسائل جديدة")
            return []
            
    except Exception as e:
        logger.error(f"❌ خطأ في سحب الرسائل: {e}")
        return []

async def update_vector_database(messages):
    """تحديث قاعدة بيانات المتجهات"""
    try:
        if not messages:
            logger.info("⏭️ لا توجد رسائل لإضافتها")
            return True
        
        logger.info("📊 تحديث قاعدة البيانات...")
        
        from vector_store import add_messages_to_db
        
        # إضافة الرسائل الجديدة
        success = add_messages_to_db(messages)
        
        if success:
            logger.info(f"✅ تم تحديث قاعدة البيانات بنجاح ({len(messages)} رسالة)")
        else:
            logger.error("❌ فشل تحديث قاعدة البيانات")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث قاعدة البيانات: {e}")
        return False

async def cleanup_old_data():
    """تنظيف البيانات القديمة"""
    try:
        logger.info("🧹 تنظيف البيانات القديمة...")
        
        # يمكنك إضافة منطق لحذف الرسائل القديمة جداً (أقدم من سنة مثلاً)
        # لكن حالياً نحتفظ بكل شيء
        
        logger.info("✅ اكتمل التنظيف")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في التنظيف: {e}")
        return False

async def main():
    """الوظيفة الرئيسية"""
    
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🚀 بدء التحديث اليومي - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # 1. سحب الرسائل الجديدة
        messages = await scrape_new_messages()
        
        # 2. تحديث قاعدة البيانات
        await update_vector_database(messages)
        
        # 3. تنظيف البيانات القديمة
        await cleanup_old_data()
        
        # حساب الوقت المستغرق
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info(f"✅ اكتمل التحديث اليومي بنجاح")
        logger.info(f"⏱️ الوقت المستغرق: {duration:.2f} ثانية")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل التحديث اليومي: {e}")
        logger.exception(e)
        return False

if __name__ == "__main__":
    # التأكد من وجود مجلد logs
    os.makedirs('logs', exist_ok=True)
    
    # تشغيل التحديث
    result = asyncio.run(main())
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
