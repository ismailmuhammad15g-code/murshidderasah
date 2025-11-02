"""
فحص محتوى قاعدة ChromaDB
"""
import chromadb
from chromadb.config import Settings

try:
    client = chromadb.PersistentClient(
        path="./db",
        settings=Settings(
            anonymized_telemetry=False,
            allow_reset=True
        )
    )
    
    # جلب جميع المجموعات
    collections = client.list_collections()
    
    print("=" * 60)
    print(f"عدد المجموعات: {len(collections)}")
    print("=" * 60)
    
    for col in collections:
        print(f"\n📦 المجموعة: {col.name}")
        count = col.count()
        print(f"   عدد المستندات: {count}")
        
        if count > 0:
            # جلب عينة
            sample = col.get(limit=3, include=['documents', 'metadatas'])
            print(f"   عينة من البيانات:")
            for i, doc in enumerate(sample['documents'], 1):
                print(f"   {i}. {doc[:100]}...")
    
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"❌ خطأ: {e}")
