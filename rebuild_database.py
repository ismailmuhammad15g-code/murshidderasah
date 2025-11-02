#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🏗️ سكريبت البناء الكامل والاحترافي لقاعدة بيانات ChromaDB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ يستخدم الـ 10 مفاتيح API بالدوران
✅ يسحب من جميع المصادر (القناة الرئيسية + جروب الإقامات)
✅ يدعم ChromaDB فقط (النسخة الاحترافية)
✅ مصمم للاستضافة القوية (Azure, AWS, VPS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import logging
import time
import os
from datetime import datetime
import scraper
import vector_store
from config import Config

# إعداد السجل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/build.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """طباعة لافتة البداية"""
    print()
    print("╔" + "═"*68 + "╗")
    print("║" + " "*17 + "🏗️  بناء قاعدة البيانات الكاملة" + " "*18 + "║")
    print("║" + " "*14 + "النسخة الاحترافية - ChromaDB + 10 مفاتيح" + " "*13 + "║")
    print("╚" + "═"*68 + "╝")
    print()


def print_config_info():
    """طباعة معلومات الإعداد"""
    num_keys = len(Config.GOOGLE_API_KEYS)
    num_sources = len([s for s in Config.TELEGRAM_SOURCES if s.get("id")])
    
    print("📊 معلومات الإعداد:")
    print("─" * 70)
    print(f"🔑 عدد مفاتيح Google API: {num_keys}")
    print(f"📡 عدد مصادر تليجرام: {num_sources}")
    print(f"⚡ السرعة المتوقعة: {num_keys}x (بالمقارنة مع مفتاح واحد)")
    print(f"📅 نطاق البيانات: آخر {Config.DAYS_LIMIT} يوم")
    print()
    
    # عرض المصادر
    print("📡 المصادر:")
    for source in Config.TELEGRAM_SOURCES:
        if source.get("id"):
            tag = source.get("tag", "unknown")
            source_type = source.get("type", "public")
            print(f"   • {tag} ({source_type}): {source['id']}")
    print()
    
    # تقدير الوقت
    if num_keys == 1:
        estimated_time = 4.5 * 60  # 4.5 ساعة بالثواني
    else:
        estimated_time = (4.5 * 60) / num_keys
    
    estimated_minutes = int(estimated_time / 60)
    if estimated_minutes < 1:
        print(f"⏱️  الوقت المتوقع: ~{int(estimated_time)} ثانية")
    else:
        print(f"⏱️  الوقت المتوقع: ~{estimated_minutes} دقيقة")
    
    print("─" * 70)
    print()


async def rebuild_full_database():
    """بناء قاعدة البيانات الكاملة من الصفر"""
    
    print_banner()
    print_config_info()
    
    # تحذير: سيتم حذف قاعدة البيانات الحالية
    db_path = Config.DB_PATH
    if os.path.exists(db_path):
        print("⚠️  تنبيه: توجد قاعدة بيانات حالية")
        print(f"   المسار: {db_path}")
        print()
        response = input("❓ هل تريد حذفها وإعادة البناء من الصفر؟ (نعم/لا): ").strip().lower()
        
        if response not in ['نعم', 'yes', 'y']:
            print()
            print("⏸️  تم إلغاء العملية")
            return False
        
        # حذف المجلد
        import shutil
        try:
            shutil.rmtree(db_path)
            logger.info(f"✅ تم حذف قاعدة البيانات القديمة: {db_path}")
        except Exception as e:
            logger.error(f"❌ فشل حذف قاعدة البيانات: {e}")
            return False
    
    print()
    print("=" * 70)
    print()
    
    # بدء المؤقت
    start_time = time.time()
    
    # ═══════════════════════════════════════════════════════════════════
    # الخطوة 1: سحب الرسائل من جميع المصادر
    # ═══════════════════════════════════════════════════════════════════
    print("📥 الخطوة 1/2: سحب الرسائل من جميع المصادر")
    print("─" * 70)
    print()
    
    # استخدام scrape_all_sources() للنسخة V2
    documents = await scraper.scrape_all_sources()
    
    if documents is None:
        print()
        print("❌ فشل سحب الرسائل!")
        print()
        print("💡 الحلول الممكنة:")
        print("   1. تأكد من صحة TELEGRAM_API_ID و TELEGRAM_API_HASH في .env")
        print("   2. تأكد أن حسابك منضم لجميع المصادر (القنوات/الجروبات)")
        print("   3. حاول حذف ملف 'anon.session' وأعد المحاولة")
        print()
        return False
    
    if len(documents) == 0:
        print()
        print("⚠️ تم سحب 0 رسالة!")
        print()
        print("💡 تأكد أن:")
        print("   • حسابك منضم لقناة @mahadalazhar")
        print("   • حسابك منضم لجروب الإقامات (إن كان مضافاً)")
        print("   • حذف ملف 'anon.session' وأعد المحاولة")
        print()
        return False
    
    print()
    print(f"✅ تم سحب {len(documents)} رسالة بنجاح!")
    print()
    
    # إحصائيات التصنيف
    admin_count = sum(1 for d in documents if d.get('type') == 'admin')
    student_count = sum(1 for d in documents if d.get('type') == 'student')
    print(f"   📊 التصنيف:")
    print(f"      • منشورات رسمية (admin): {admin_count}")
    print(f"      • نقاشات طلاب (student): {student_count}")
    print()
    
    # إحصائيات المصادر
    source_counts = {}
    for doc in documents:
        tag = doc.get('source_tag', 'unknown')
        source_counts[tag] = source_counts.get(tag, 0) + 1
    
    if len(source_counts) > 1:
        print(f"   📡 توزيع المصادر:")
        for tag, count in source_counts.items():
            print(f"      • {tag}: {count} رسالة")
        print()
    
    # ═══════════════════════════════════════════════════════════════════
    # الخطوة 2: بناء قاعدة المتجهات
    # ═══════════════════════════════════════════════════════════════════
    print("─" * 70)
    print("🏗️  الخطوة 2/2: بناء قاعدة المتجهات (ChromaDB)")
    print("─" * 70)
    print()
    
    num_keys = len(Config.GOOGLE_API_KEYS)
    total_batches = (len(documents) + 39) // 40
    
    print(f"📊 معلومات المعالجة:")
    print(f"   • إجمالي الرسائل: {len(documents)}")
    print(f"   • حجم الدفعة: 40 رسالة")
    print(f"   • عدد الدفعات: {total_batches}")
    print(f"   • عدد المفاتيح: {num_keys}")
    print(f"   • السرعة: {num_keys}x")
    print()
    print("⏳ جاري المعالجة... (قد يستغرق دقائق)")
    print()
    
    vector_store.build_database(documents)
    
    # ═══════════════════════════════════════════════════════════════════
    # النتيجة النهائية
    # ═══════════════════════════════════════════════════════════════════
    elapsed_time = time.time() - start_time
    elapsed_minutes = int(elapsed_time / 60)
    elapsed_seconds = int(elapsed_time % 60)
    
    print()
    print("=" * 70)
    print("🎉 اكتمل بناء قاعدة البيانات بنجاح!")
    print("=" * 70)
    print()
    print(f"✅ تم معالجة: {len(documents)} رسالة")
    print(f"   • رسمية (admin): {admin_count}")
    print(f"   • طلاب (student): {student_count}")
    print()
    
    if len(source_counts) > 1:
        print(f"📡 المصادر:")
        for tag, count in source_counts.items():
            print(f"   • {tag}: {count}")
        print()
    
    print(f"⏱️  الوقت الفعلي: {elapsed_minutes} دقيقة و {elapsed_seconds} ثانية")
    print(f"🔥 السرعة: {num_keys}x (باستخدام {num_keys} مفتاح)")
    print(f"💾 قاعدة البيانات: {db_path}")
    print()
    print("=" * 70)
    print()
    print("✨ البوت جاهز الآن للإنتاج!")
    print()
    print("▶️  للتشغيل:")
    print("   python main.py              (وضع Polling)")
    print("   python flask_app.py         (وضع Webhook)")
    print()
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    """نقطة الدخول الرئيسية"""
    
    # إنشاء مجلد logs إن لم يكن موجوداً
    os.makedirs("logs", exist_ok=True)
    
    print()
    logger.info("بدء سكريبت البناء الكامل...")
    print()
    
    try:
        success = asyncio.run(rebuild_full_database())
        
        if not success:
            print()
            print("=" * 70)
            print("❌ فشلت عملية البناء")
            print("=" * 70)
            print()
            print("💡 راجع ملف logs/build.log للمزيد من التفاصيل")
            print()
            exit(1)
        else:
            exit(0)
    
    except KeyboardInterrupt:
        print()
        print()
        print("⏸️  تم إيقاف العملية بواسطة المستخدم")
        print()
        exit(1)
    
    except Exception as e:
        logger.exception(f"❌ خطأ فادح: {e}")
        print()
        print("=" * 70)
        print("❌ حدث خطأ غير متوقع")
        print("=" * 70)
        print()
        print(f"الخطأ: {e}")
        print()
        print("💡 راجع ملف logs/build.log للمزيد من التفاصيل")
        print()
        exit(1)
