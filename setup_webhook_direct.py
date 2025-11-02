"""
===================================
setup_webhook_direct.py - تفعيل Webhook مباشرة
===================================

استخدام Telegram API مباشرة بدون مكتبة python-telegram-bot
لتجنب مشاكل التوافق

الاستخدام:
    python setup_webhook_direct.py
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def main():
    """إعداد Webhook للبوت باستخدام Telegram API مباشرة"""
    
    print("=" * 60)
    print("🚀 إعداد Webhook لبوت مرشد الدراسة")
    print("=" * 60)
    
    # الحصول على التوكن
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        print("\n❌ خطأ: لم يتم العثور على BOT_TOKEN في ملف .env")
        return False
    
    # طلب رابط الموقع
    print("\n📌 أدخل رابط موقعك على PythonAnywhere:")
    print("   مثال: https://murshidderasah.pythonanywhere.com")
    
    website_url = input("\n🔗 رابط الموقع: ").strip()
    
    if not website_url:
        print("❌ لم تدخل رابط الموقع!")
        return False
    
    # التأكد من أن الرابط يبدأ بـ https://
    if not website_url.startswith("http"):
        website_url = f"https://{website_url}"
    
    # إزالة / من نهاية الرابط
    website_url = website_url.rstrip("/")
    
    # إنشاء رابط الـ Webhook
    webhook_url = f"{website_url}/webhook"
    
    print(f"\n📌 رابط الموقع: {website_url}")
    print(f"📌 رابط Webhook: {webhook_url}")
    print(f"📌 توكن البوت: {bot_token[:20]}...")
    
    try:
        print("\n⏳ جاري الاتصال بـ Telegram API...")
        
        # استدعاء Telegram API مباشرة
        api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        
        response = requests.post(api_url, json={
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query"]
        })
        
        result = response.json()
        
        if result.get("ok"):
            print("\n✅ نجح إعداد Webhook!")
            print(f"\n📊 الرد من Telegram:")
            print(f"  - الحالة: {result.get('description', 'تم الإعداد بنجاح')}")
            
            # الحصول على معلومات Webhook
            info_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
            info_response = requests.get(info_url)
            info_result = info_response.json()
            
            if info_result.get("ok"):
                info = info_result.get("result", {})
                print(f"\n📌 معلومات Webhook:")
                print(f"  - الرابط: {info.get('url', 'غير متاح')}")
                print(f"  - عدد التحديثات المعلقة: {info.get('pending_update_count', 0)}")
                if info.get('last_error_message'):
                    print(f"  - آخر خطأ: {info.get('last_error_message')}")
                else:
                    print(f"  - آخر خطأ: لا يوجد ✅")
            
            print("\n🎉 البوت الآن يعمل عبر Webhook!")
            print(f"💡 جرّب البوت: @murshidderasahbot")
            print("\n⚠️ ملاحظة: إذا لم يعمل البوت، تأكد من:")
            print("   1. إعادة تحميل الموقع من لوحة Web في PythonAnywhere")
            print("   2. التأكد من أن flask_app.py يعمل بدون أخطاء")
            print("   3. فحص Error log في PythonAnywhere")
            
            return True
        else:
            print(f"\n❌ فشل إعداد Webhook:")
            print(f"   {result.get('description', 'خطأ غير معروف')}")
            return False
        
    except Exception as e:
        print(f"\n❌ فشل إعداد Webhook:")
        print(f"   {str(e)}")
        print("\n🔍 تحقق من:")
        print("  1. توكن البوت صحيح")
        print("  2. رابط الموقع صحيح ويعمل")
        print("  3. الموقع يدعم HTTPS (مطلوب لـ Telegram)")
        print("  4. اتصال الإنترنت يعمل")
        return False

if __name__ == "__main__":
    print("\n")
    result = main()
    
    if result:
        print("\n✅ تم بنجاح!")
    else:
        print("\n❌ فشلت العملية")
