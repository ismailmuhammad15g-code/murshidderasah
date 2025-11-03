"""
Simple webhook setup using requests (no telegram library needed)
"""
import requests
from config import Config

def setup_webhook():
    """Setup webhook using simple HTTP request"""
    
    # Remove trailing slash
    base_url = Config.WEBSITE_URL.rstrip('/')
    webhook_url = f"{base_url}/webhook"
    
    print("=" * 60)
    print("🚀 إعداد Webhook (الطريقة البسيطة)")
    print("=" * 60)
    print(f"\n📋 رابط Webhook: {webhook_url}")
    print(f"📋 توكن البوت: {Config.BOT_TOKEN[:20]}...")
    
    # Telegram API endpoint
    api_url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/setWebhook"
    
    try:
        print("\n⏳ جاري إرسال الطلب...")
        response = requests.post(api_url, json={"url": webhook_url}, timeout=30)
        result = response.json()
        
        if result.get("ok"):
            print("\n✅ نجح إعداد Webhook!")
            print(f"   الوصف: {result.get('description', 'تم بنجاح')}")
            
            # Get webhook info
            info_url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/getWebhookInfo"
            info_response = requests.get(info_url, timeout=30)
            info = info_response.json()
            
            if info.get("ok"):
                webhook_info = info.get("result", {})
                print("\n📊 معلومات Webhook:")
                print(f"   الرابط: {webhook_info.get('url')}")
                print(f"   التحديثات المعلقة: {webhook_info.get('pending_update_count', 0)}")
                if webhook_info.get('last_error_message'):
                    print(f"   آخر خطأ: {webhook_info.get('last_error_message')}")
            
            print("\n🎉 البوت الآن يعمل عبر Webhook!")
            return True
        else:
            print(f"\n❌ فشل: {result.get('description', 'خطأ غير معروف')}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ انتهت مهلة الاتصال")
        print("💡 تأكد من أن الموقع يعمل ويمكن الوصول إليه")
        return False
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
        return False

if __name__ == "__main__":
    success = setup_webhook()
    exit(0 if success else 1)
