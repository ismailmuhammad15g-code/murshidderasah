import vector_store_faiss as vs

print("🧪 اختبار FAISS...")

# اختبار بحث
results = vs.search_database('ما هي شروط الزكاة؟', top_k=5)

print(f"\n✅ النتائج: {len(results)}")

if results:
    print("\n📋 أفضل 3 نتائج:")
    for i, r in enumerate(results[:3], 1):
        print(f"\n{i}. النوع: {r.get('type', '؟')}")
        print(f"   النص: {r.get('text', '')[:100]}...")
        print(f"   المسافة: {r.get('distance', 0):.4f}")
    
    print("\n✅ الاختبار ناجح!")
else:
    print("\n❌ لم يتم العثور على نتائج")
