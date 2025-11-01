"""
===================================
delete_webhook.py - حذف Webhook
===================================

هذا السكريبت يقوم بحذف Webhook من البوت
مفيد عندما تريد العودة للاختبار المحلي

الاستخدام:
    python delete_webhook.py
"""

import asyncio
import sys
from config import Config

async def main():
    """حذف Webhook من البوت"""
    
    print("=" * 60)
    print("🗑️ حذف Webhook من بوت مرشد الدراسة")
    print("=" * 60)
    
    # التحقق من وجود BOT_TOKEN
    if not Config.BOT_TOKEN:
        print("\n❌ خطأ: لم يتم العثور على BOT_TOKEN في ملف .env")
        return False
    
    try:
        from telegram.ext import Application
        
        print("\n⏳ جاري الاتصال بـ Telegram...")
        
        # إنشاء التطبيق
        app = Application.builder().token(Config.BOT_TOKEN).build()
        
        # حذف الـ Webhook
        await app.bot.delete_webhook()
        
        print("\n✅ تم حذف Webhook بنجاح!")
        print("\n💡 الآن يمكنك تشغيل البوت محلياً باستخدام:")
        print("   python main.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ فشل حذف Webhook:")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    print("\n")
    result = asyncio.run(main())
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
