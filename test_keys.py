from config import Config

print(f"🔥 تم تحميل {len(Config.GOOGLE_API_KEYS)} مفتاح Google API")
print()
print("المفاتيح المحملة:")
for i, key in enumerate(Config.GOOGLE_API_KEYS, 1):
    print(f"  {i}. {key[:25]}...")
