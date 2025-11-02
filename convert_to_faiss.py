"""
===================================
rebuild_database.py - تحويل ChromaDB إلى FAISS
===================================

هذا السكريبت يقوم بتحويل قاعدة ChromaDB الموجودة
إلى ملفات FAISS الخفيفة

الاستخدام:
    python rebuild_database.py
"""

import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_chromadb_to_faiss():
    """تحويل قاعدة ChromaDB إلى FAISS"""
    
    logger.info("=" * 60)
    logger.info("🔄 بدء تحويل ChromaDB إلى FAISS")
    logger.info("=" * 60)
    
    try:
        # استيراد المكتبات
        logger.info("📦 تحميل المكتبات...")
        
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            logger.error("❌ ChromaDB غير مثبت!")
            logger.error("💡 قم بتثبيته: pip install chromadb")
            return False
        
        import vector_store_faiss as faiss_store
        from config import Config
        
        # الاتصال بـ ChromaDB القديم
        logger.info("🔌 الاتصال بـ ChromaDB...")
        
        client = chromadb.PersistentClient(
            path=Config.DB_PATH,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # جلب المجموعة
        try:
            # محاولة أسماء مختلفة للمجموعة
            collection_names = ["morshed_db", "school_messages", "messages"]
            collection = None
            
            for name in collection_names:
                try:
                    collection = client.get_collection(name)
                    logger.info(f"✅ تم العثور على المجموعة: {name}")
                    break
                except:
                    continue
            
            if collection is None:
                # جلب جميع المجموعات الموجودة
                all_collections = client.list_collections()
                if all_collections:
                    collection = all_collections[0]
                    logger.info(f"✅ استخدام المجموعة: {collection.name}")
                else:
                    raise Exception("لا توجد مجموعات في قاعدة البيانات")
                    
        except Exception as e:
            logger.error(f"❌ لم يتم العثور على أي مجموعة: {e}")
            logger.error("💡 تأكد من أن قاعدة ChromaDB موجودة في: " + Config.DB_PATH)
            return False
        
        # جلب جميع البيانات
        logger.info("📥 جلب جميع البيانات من ChromaDB...")
        
        # جلب عدد المستندات أولاً
        total_count = collection.count()
        logger.info(f"📊 عدد المستندات في المجموعة: {total_count}")
        
        # جلب البيانات على دفعات
        batch_size = 1000
        all_documents = []
        all_metadatas = []
        
        for offset in range(0, total_count, batch_size):
            logger.info(f"⏳ جلب دفعة {offset//batch_size + 1}/{(total_count + batch_size - 1)//batch_size}...")
            
            batch = collection.get(
                limit=batch_size,
                offset=offset,
                include=['documents', 'metadatas']
            )
            
            if batch and batch.get('documents'):
                all_documents.extend(batch['documents'])
                all_metadatas.extend(batch.get('metadatas', [{}] * len(batch['documents'])))
        
        total_docs = len(all_documents)
        logger.info(f"✅ تم جلب {total_docs} مستند")
        
        if total_docs == 0:
            logger.error("❌ لا توجد مستندات في قاعدة البيانات!")
            return False
        
        # تحويل إلى صيغة FAISS
        logger.info("🔄 تحويل البيانات...")
        
        documents = []
        for i in range(total_docs):
            metadata = all_metadatas[i] if i < len(all_metadatas) else {}
            doc = {
                'text': all_documents[i],
                'link': metadata.get('link', ''),
                'type': metadata.get('type', 'student'),
                'date': metadata.get('date', '')
            }
            documents.append(doc)
        
        # بناء قاعدة FAISS
        logger.info("🚀 بناء قاعدة FAISS...")
        
        success = faiss_store.build_database(documents)
        
        if success:
            logger.info("=" * 60)
            logger.info("✅ اكتمل التحويل بنجاح!")
            logger.info("📁 الملفات الجديدة:")
            logger.info(f"   - {faiss_store.FAISS_INDEX_FILE}")
            logger.info(f"   - {faiss_store.METADATA_FILE}")
            logger.info("=" * 60)
            logger.info("💡 يمكنك الآن:")
            logger.info("   1. حذف مجلد db/ القديم (لتوفير المساحة)")
            logger.info("   2. رفع الملفين الجديدين إلى PythonAnywhere")
            logger.info("   3. استخدام vector_store_faiss.py في المشروع")
            logger.info("=" * 60)
            return True
        else:
            logger.error("❌ فشل بناء قاعدة FAISS!")
            return False
        
    except Exception as e:
        logger.error(f"❌ خطأ في التحويل: {e}")
        logger.exception(e)
        return False

def test_faiss_search():
    """اختبار البحث في قاعدة FAISS"""
    
    logger.info("🧪 اختبار البحث في FAISS...")
    
    try:
        import vector_store_faiss as faiss_store
        
        # اختبار بحث بسيط
        test_query = "ما هي شروط الزكاة؟"
        logger.info(f"🔍 الاستعلام: {test_query}")
        
        results = faiss_store.search_database(test_query, top_k=5)
        
        if results:
            logger.info(f"✅ تم العثور على {len(results)} نتيجة")
            logger.info("\n📋 أفضل 3 نتائج:")
            for i, result in enumerate(results[:3], 1):
                logger.info(f"\n{i}. النوع: {result.get('type', '؟')}")
                logger.info(f"   النص: {result.get('text', '')[:100]}...")
                logger.info(f"   المسافة: {result.get('distance', 0):.4f}")
            
            return True
        else:
            logger.error("❌ لم يتم العثور على نتائج!")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في الاختبار: {e}")
        logger.exception(e)
        return False

def main():
    """الوظيفة الرئيسية"""
    
    print("\n")
    logger.info("🎯 سكريبت تحويل ChromaDB إلى FAISS")
    print("\n")
    
    # التحويل
    success = convert_chromadb_to_faiss()
    
    if not success:
        logger.error("❌ فشل التحويل!")
        sys.exit(1)
    
    # الاختبار
    print("\n")
    test_success = test_faiss_search()
    
    if test_success:
        logger.info("=" * 60)
        logger.info("🎉 النجاح الكامل! قاعدة FAISS جاهزة للاستخدام")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.warning("⚠️ التحويل نجح لكن الاختبار فشل")
        logger.info("💡 قد تحتاج لإعادة المحاولة")
        sys.exit(1)

if __name__ == "__main__":
    main()
