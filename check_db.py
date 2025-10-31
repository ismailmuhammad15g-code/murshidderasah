import json
import os

db_path = "db/lite_store.json"

if os.path.exists(db_path):
    with open(db_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    docs = data.get("docs", [])
    print(f"✅ قاعدة البيانات موجودة")
    print(f"📊 عدد الرسائل: {len(docs)}")
    
    if len(docs) > 0:
        print(f"\n🔍 عينة من أول رسالة:")
        first_doc = docs[0]
        print(f"  - ID: {first_doc.get('id', 'N/A')}")
        print(f"  - النص: {first_doc.get('text', 'N/A')[:100]}...")
        print(f"  - الرابط: {first_doc.get('link', 'N/A')}")
        print(f"  - لديها embedding: {'✅ نعم' if first_doc.get('embedding') else '❌ لا'}")
        
        if first_doc.get('embedding'):
            print(f"  - طول الـ embedding: {len(first_doc['embedding'])}")
    else:
        print("\n⚠️ قاعدة البيانات فارغة! لم يتم بناؤها بعد.")
else:
    print("❌ قاعدة البيانات غير موجودة!")
