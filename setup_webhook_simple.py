"""
===================================
setup_webhook_simple.py - تفعيل Webhook بطريقة مبسطة
===================================

هذا السكريبت البديل لا يحتاج WEBSITE_URL في config.py
يمكنك تشغيله مباشرة على PythonAnywhere

الاستخدام:
    python setup_webhook_simple.py
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    """إعداد Webhook للبوت"""
    
    print("=" * 60)
    print("🚀 إعداد Webhook لبوت مرشد الدراسة")
    print("=" * 60)
    
    # الحصول على التوكن
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        print("\n❌ خطأ: لم يتم العثور على BOT_TOKEN في ملف .env")
        print("\nيرجى إضافة توكن البوت في ملف .env:")
        print("BOT_TOKEN=your_bot_token_here")
        return False
    
    # طلب رابط الموقع من المستخدم
    print("\n📌 أدخل رابط موقعك على PythonAnywhere:")
    print("   مثال: https://murshidderasah.pythonanywhere.com")
    
    website_url = input("\n🔗 رابط الموقع: ").strip()
    
    if not website_url:
        print("❌ لم تدخل رابط الموقع!")
        return False
    
    # التأكد من أن الرابط يبدأ بـ https://
    if not website_url.startswith("http"):
        website_url = f"https://{website_url}"
    
    # إزالة / من نهاية الرابط إذا وجد
    website_url = website_url.rstrip("/")
    
    # إنشاء رابط الـ Webhook
    webhook_url = f"{website_url}/webhook"
    
    print(f"\n📌 رابط الموقع: {website_url}")
    print(f"📌 رابط Webhook: {webhook_url}")
    print(f"📌 توكن البوت: {bot_token[:20]}...")
    
    try:
        from telegram.ext import Application
        
        print("\n⏳ جاري الاتصال بـ Telegram...")
        
        # إنشاء التطبيق
        app = Application.builder().token(bot_token).build()
        
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
        print(f"💡 جرّب البوت: @murshidderasahbot")
        print("\n⚠️ ملاحظة: إذا لم يعمل البوت، تأكد من:")
        print("   1. إعادة تحميل الموقع من لوحة Web في PythonAnywhere")
        print("   2. التأكد من أن flask_app.py يعمل بدون أخطاء")
        
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
