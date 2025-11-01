"""
===================================
set_webhook.py - إعداد Webhook للبوت
===================================

هذا السكريبت يقوم بربط بوت التليجرام بموقعك على PythonAnywhere
يتم تشغيله مرة واحدة فقط بعد نشر الموقع

الاستخدام:
    python set_webhook.py
"""

import asyncio
import sys
from config import Config

async def main():
    """إعداد Webhook للبوت"""
    
    print("=" * 60)
    print("🚀 إعداد Webhook لبوت مرشد الدراسة")
    print("=" * 60)
    
    # التحقق من وجود WEBSITE_URL
    if not Config.WEBSITE_URL:
        print("\n❌ خطأ: لم يتم العثور على WEBSITE_URL في ملف .env")
        print("\nيرجى إضافة رابط موقعك في ملف .env:")
        print("WEBSITE_URL=https://yourusername.pythonanywhere.com")
        print("\nمثال:")
        print("WEBSITE_URL=https://ismail15g.pythonanywhere.com")
        return False
    
    # التحقق من وجود BOT_TOKEN
    if not Config.BOT_TOKEN:
        print("\n❌ خطأ: لم يتم العثور على BOT_TOKEN في ملف .env")
        print("\nيرجى إضافة توكن البوت في ملف .env:")
        print("BOT_TOKEN=your_bot_token_here")
        return False
    
    # إنشاء رابط الـ Webhook
    webhook_url = f"{Config.WEBSITE_URL}/webhook"
    
    print(f"\n📌 رابط الموقع: {Config.WEBSITE_URL}")
    print(f"📌 رابط Webhook: {webhook_url}")
    print(f"📌 توكن البوت: {Config.BOT_TOKEN[:20]}...")
    
    try:
        from telegram.ext import Application
        
        print("\n⏳ جاري الاتصال بـ Telegram...")
        
        # إنشاء التطبيق
        app = Application.builder().token(Config.BOT_TOKEN).build()
        
        # إعداد الـ Webhook
        await app.bot.set_webhook(webhook_url)
        
        # التحقق من الإعداد
        webhook_info = await app.bot.get_webhook_info()
        
        print("\n✅ نجح إعداد Webhook!")
        print("\n📊 معلومات Webhook:")
        print(f"  - الرابط: {webhook_info.url}")
        print(f"  - عدد التحديثات المعلقة: {webhook_info.pending_update_count}")
        print(f"  - آخر خطأ: {webhook_info.last_error_message if webhook_info.last_error_message else 'لا يوجد'}")
        
        print("\n🎉 البوت الآن يعمل عبر Webhook!")
        print("💡 ملاحظة: البوت لن يعمل على جهازك المحلي بعد الآن")
        print("   لإلغاء Webhook، استخدم: python delete_webhook.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ فشل إعداد Webhook:")
        print(f"   {str(e)}")
        print("\n🔍 تحقق من:")
        print("  1. توكن البوت صحيح")
        print("  2. رابط الموقع صحيح ويعمل")
        print("  3. الموقع يدعم HTTPS (مطلوب لـ Telegram)")
        return False

if __name__ == "__main__":
    print("\n")
    result = asyncio.run(main())
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
