# vector_store.py
import google.generativeai as genai
import logging
import time
import os
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# إعداد Google AI - دعم مفاتيح متعددة
GOOGLE_API_KEYS = Config.GOOGLE_API_KEYS
EMBEDDING_MODEL = Config.GEMINI_EMBED_MODEL

# متغير لتتبع المفتاح الحالي (دائري)
_current_key_index = 0

def _get_next_api_key():
    """اختيار المفتاح التالي بشكل دائري (Round Robin)"""
    global _current_key_index
    key = GOOGLE_API_KEYS[_current_key_index]
    _current_key_index = (_current_key_index + 1) % len(GOOGLE_API_KEYS)
    return key

logger.info(f"✅ تم تحميل {len(GOOGLE_API_KEYS)} مفتاح Google API")

# تهيئة ChromaDB
collection = None
client = None

# محاولة استيراد ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    logger.info("✅ تم استيراد ChromaDB بنجاح")
except ImportError as e:
    logger.critical("!" * 60)
    logger.critical("❌ خطأ فادح: لم يتم العثور على مكتبة ChromaDB!")
    logger.critical("🔧 الحل: قم بتشغيل: pip install chromadb")
    logger.critical("!" * 60)
    raise e


def _ensure_db_dir():
    """إنشاء مجلد قاعدة البيانات إذا لم يكن موجوداً"""
    os.makedirs(Config.DB_PATH, exist_ok=True)


def _init_chromadb():
    """تهيئة ChromaDB - يجب أن تنجح وإلا سيتوقف البرنامج"""
    global client, collection
    
    if collection is not None:
        return  # تم التهيئة مسبقاً
    
    _ensure_db_dir()
    
    try:
        # استخدام HttpClient بدلاً من PersistentClient لتجنب مشكلة hnswlib
        # أو استخدام EphemeralClient للاختبار
        logger.info("🔄 محاولة الاتصال بـ ChromaDB...")
        
        # الطريقة 1: استخدام PersistentClient (يحتاج hnswlib)
        try:
            client = chromadb.PersistentClient(path=Config.DB_PATH)
            logger.info("✅ تم الاتصال بـ ChromaDB (PersistentClient)")
        except Exception as persist_error:
            logger.warning(f"⚠️ فشل PersistentClient: {persist_error}")
            logger.info("🔄 محاولة استخدام EphemeralClient (في الذاكرة)...")
            client = chromadb.Client()
            logger.info("✅ تم الاتصال بـ ChromaDB (EphemeralClient - في الذاكرة)")
        
        collection = client.get_or_create_collection(name="morshed_db")
        logger.info(f"✅ تم إنشاء/فتح المجموعة 'morshed_db'")
        
    except Exception as e:
        logger.critical("!" * 60)
        logger.critical(f"❌ خطأ فادح في تهيئة ChromaDB: {e}")
        logger.critical("💡 السبب المحتمل: مكتبة hnswlib غير مُثبتة")
        logger.critical("🔧 الحل:")
        logger.critical("   1. ثبّت Visual C++ Build Tools من:")
        logger.critical("      https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        logger.critical("   2. ثم شغّل: pip install hnswlib")
        logger.critical("   3. أو شغّل: pip install chroma-hnswlib")
        logger.critical("!" * 60)
        raise e  # أوقف البرنامج


def get_embedding(text_chunk: str):
    """الحصول على embedding من Google API مع دعم مفاتيح متعددة"""
    if not text_chunk or text_chunk.isspace():
        return None
    
    # 🔥 اختيار المفتاح التالي بشكل دائري
    api_key = _get_next_api_key()
    
    try:
        # تهيئة genai بالمفتاح الحالي
        genai.configure(api_key=api_key)
        
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text_chunk,
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']
        
    except Exception as e:
        error_msg = str(e)
        
        # معالجة خطأ 429 (Rate Limit)
        if "429" in error_msg or "quota" in error_msg.lower():
            logger.warning(f"⚠️ تم الوصول لحد المفتاح. الانتقال للمفتاح التالي...")
            # إذا لدينا مفاتيح متعددة، جرّب التالي
            if len(GOOGLE_API_KEYS) > 1:
                return get_embedding(text_chunk)  # محاولة أخرى بمفتاح جديد
            else:
                logger.error("⏳ لدينا مفتاح واحد فقط. سيتم الانتظار 65 ثانية...")
                time.sleep(65)
                return get_embedding(text_chunk)
        
        logger.error(f"❌ فشل عمل embedding: {error_msg}")
        return None


def build_database(documents: list):
    """بناء قاعدة بيانات المتجهات مع Batch Processing الحقيقي (40x أسرع)"""
    _init_chromadb()
    
    num_keys = len(GOOGLE_API_KEYS)
    logger.info(f"🏛️ بدء بناء قاعدة بيانات المتجهات لـ {len(documents)} رسالة...")
    logger.info(f"🔥 استخدام {num_keys} مفتاح - سرعة {num_keys}x")
    logger.info(f"⚡ استخدام Batch Embeddings API (40x أسرع)")
    
    BATCH_SIZE = 40
    total_docs = len(documents)
    total_batches = (total_docs + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, total_docs, BATCH_SIZE):
        batch_documents = documents[i: i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info(f"🔄 معالجة الدفعة {batch_num}/{total_batches} ({len(batch_documents)} رسالة)...")

        # 1️⃣ فلترة الرسائل: فقط الجديدة + لها نص صالح
        docs_to_process = []
        for doc in batch_documents:
            # تحقق إذا كانت موجودة مسبقاً
            try:
                existing = collection.get(ids=[doc["id"]])
                if existing and existing['ids']:
                    logger.debug(f"✅ الرسالة {doc['id']} موجودة بالفعل. تخطي...")
                    continue
            except Exception:
                pass
            
            # تحقق من صحة النص
            if doc['text'] and not doc['text'].isspace():
                docs_to_process.append(doc)
        
        if not docs_to_process:
            logger.info("⚠️ لا توجد رسائل جديدة في هذه الدفعة")
            continue
        
        # 2️⃣ تجميع النصوص في قائمة واحدة
        batch_texts = [doc['text'] for doc in docs_to_process]
        
        try:
            # 3️⃣ اختيار المفتاح الدائري
            key_index = (batch_num - 1) % num_keys
            api_key = GOOGLE_API_KEYS[key_index]
            genai.configure(api_key=api_key)
            
            # 4️⃣ طلب API واحد فقط للدفعة كاملة (40 embedding دفعة واحدة)
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=batch_texts,  # ✅ قائمة كاملة بدلاً من نص واحد
                task_type="RETRIEVAL_DOCUMENT"
            )
            
            embeddings = result['embedding']
            
            # 5️⃣ التحقق من التطابق
            if len(embeddings) != len(batch_texts):
                logger.warning(f"⚠️ عدم تطابق: {len(embeddings)} embeddings vs {len(batch_texts)} texts")
                continue
            
            # 6️⃣ تحضير البيانات للإضافة (مع source_tag)
            ids_to_add = [doc['id'] for doc in docs_to_process]
            metadatas_to_add = [
                {
                    'link': doc['link'],
                    'date': doc['date'],
                    'text': doc['text'],
                    'type': doc.get('type', 'admin'),  # 🏷️ نوع الرسالة
                    'source_tag': doc.get('source_tag', 'public_channel')  # 🆕 V2: بطاقة المصدر
                }
                for doc in docs_to_process
            ]
            
            # 7️⃣ إضافة الدفعة إلى ChromaDB
            collection.add(
                embeddings=embeddings,
                metadatas=metadatas_to_add,
                ids=ids_to_add
            )
            logger.info(f"✅ تمت إضافة {len(embeddings)} رسالة لـ ChromaDB")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ فشل معالجة الدفعة {batch_num}: {error_msg}")
            
            # معالجة Rate Limit
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning(f"⏳ Rate Limit. الانتظار 65 ثانية...")
                time.sleep(65)
                continue
        
        # 8️⃣ الانتظار بعد كل دورة كاملة
        if i + BATCH_SIZE < total_docs:
            if batch_num % num_keys == 0:
                logger.warning(f"⏳ اكتملت دورة كاملة ({num_keys} دفعات). الانتظار 65 ثانية...")
                time.sleep(65)
            else:
                logger.info(f"⚡ الانتقال للمفتاح التالي ({(batch_num % num_keys) + 1}/{num_keys})")

    logger.info(f"🎉 اكتمل بناء قاعدة البيانات! تم معالجة {total_docs} رسالة.")


def search_database(query_text: str):
    """
    V2: البحث الهجين الذكي مع أولوية للمصادر المتخصصة
    - يكتشف الكلمات المفتاحية (مثل "إقامة") ويبحث في المصدر المناسب أولاً
    - يبحث في منشورات الأدمن (رسمي) + نقاشات الطلاب (سياق)
    """
    _init_chromadb()
    logger.info(f"🔍 V2: بدء البحث الهجين الذكي عن: {query_text}...")
    
    unique_results = {}  # لتخزين النتائج الفريدة
    
    try:
        # التأكد من وجود API key صالح للبحث
        api_key = _get_next_api_key()
        genai.configure(api_key=api_key)
        
        query_embedding = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=query_text,
            task_type="RETRIEVAL_QUERY"
        )['embedding']
        
        # 🆕 V2: البحث الذكي - إذا كان السؤال عن الإقامة، ابحث في جروب الإقامات أولاً!
        query_lower = query_text.lower()
        accommodation_keywords = ["اقامة", "إقامة", "سكن", "مبيت", "accommodation"]
        
        if any(keyword in query_lower for keyword in accommodation_keywords):
            logger.info("🎯 تم اكتشاف كلمات مفتاحية للإقامة. البحث في جروب الإقامات أولاً...")
            accommodation_results = collection.query(
                query_embeddings=[query_embedding],
                where={"source_tag": "accommodations"},  # 🔍 الفلتر السحري!
                n_results=10  # نأخذ المزيد من النتائج لأنها متخصصة
            )
            if accommodation_results and accommodation_results['metadatas'] and accommodation_results['metadatas'][0]:
                logger.info(f"✅ البحث (الإقامات) وجد: {len(accommodation_results['metadatas'][0])} نتيجة")
                for meta in accommodation_results['metadatas'][0]:
                    if meta['link'] not in unique_results:
                        unique_results[meta['link']] = {
                            "text": meta['text'], 
                            "link": meta['link'], 
                            "type": meta.get('type', 'admin'),
                            "source_tag": "accommodations"  # لتمييز المصدر
                        }

        # --- 1. البحث في منشورات الأدمن (الأولوية القصوى) ---
        admin_results = collection.query(
            query_embeddings=[query_embedding],
            where={"type": "admin"},  # الفلتر الرسمي
            n_results=5  # أفضل 5 نتائج رسمية
        )
        if admin_results and admin_results['metadatas'] and admin_results['metadatas'][0]:
            logger.info(f"✅ البحث (أدمن) وجد: {len(admin_results['metadatas'][0])} نتيجة")
            for meta in admin_results['metadatas'][0]:
                if meta['link'] not in unique_results:
                    unique_results[meta['link']] = {
                        "text": meta['text'], 
                        "link": meta['link'], 
                        "type": "admin"
                    }

        # --- 2. البحث في نقاشات الطلاب (للسياق) ---
        student_results = collection.query(
            query_embeddings=[query_embedding],
            where={"type": "student"},  # فلتر النقاشات
            n_results=5  # أفضل 5 نتائج من النقاشات
        )
        if student_results and student_results['metadatas'] and student_results['metadatas'][0]:
            logger.info(f"✅ البحث (طلاب) وجد: {len(student_results['metadatas'][0])} نتيجة")
            for meta in student_results['metadatas'][0]:
                if meta['link'] not in unique_results:
                    unique_results[meta['link']] = {
                        "text": meta['text'], 
                        "link": meta['link'], 
                        "type": "student"
                    }

    except Exception as e:
        logger.error(f"❌ فشل البحث بالمعنى: {e}")
        return []

    # --- 3. إرجاع النتائج المجمعة ---
    final_evidence = list(unique_results.values())
    logger.info(f"✅ تم العثور على {len(final_evidence)} دليل (هجين).")
    return final_evidence


def add_new_messages(documents: list):
    """
    إضافة رسائل جديدة لقاعدة البيانات (للتحديث الآلي)
    
    Args:
        documents: قائمة من الرسائل الجديدة
    
    Returns:
        عدد الرسائل التي تمت إضافتها
    """
    if not documents:
        return 0
    
    _init_chromadb()
    logger.info(f"🔄 محاولة إضافة {len(documents)} رسالة جديدة...")
    
    added_count = 0
    
    try:
        # فلترة الرسائل الجديدة فقط
        docs_to_add = []
        for doc in documents:
            try:
                existing = collection.get(ids=[doc["id"]])
                if existing and existing['ids']:
                    continue  # موجودة مسبقاً
            except Exception:
                pass
            
            if doc['text'] and not doc['text'].isspace():
                docs_to_add.append(doc)
        
        if not docs_to_add:
            logger.info("ℹ️ لا توجد رسائل جديدة لإضافتها")
            return 0
        
        # إنشاء embeddings باستخدام Batch API
        batch_texts = [doc['text'] for doc in docs_to_add]
        
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=batch_texts,
            task_type="RETRIEVAL_DOCUMENT"
        )
        
        embeddings = result['embedding']
        
        if len(embeddings) != len(batch_texts):
            logger.warning(f"⚠️ عدم تطابق embeddings")
            return 0
        
        # إضافة لقاعدة البيانات
        ids_to_add = [doc['id'] for doc in docs_to_add]
        metadatas_to_add = [
            {
                'link': doc['link'],
                'date': doc['date'],
                'text': doc['text'],
                'type': doc.get('type', 'admin')  # 🏷️ إضافة البطاقة
            }
            for doc in docs_to_add
        ]
        
        collection.add(
            embeddings=embeddings,
            metadatas=metadatas_to_add,
            ids=ids_to_add
        )
        
        added_count = len(embeddings)
        logger.info(f"✅ تمت إضافة {added_count} رسالة جديدة")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة الرسائل الجديدة: {e}")
    
    return added_count


def delete_old_messages(days: int = 365):
    """
    حذف الرسائل القديمة من قاعدة البيانات
    
    Args:
        days: عدد الأيام (افتراضي 365 يوم)
    
    Returns:
        عدد الرسائل التي تم حذفها
    """
    from datetime import datetime, timedelta, timezone
    
    _init_chromadb()
    logger.info(f"🧹 بدء تنظيف الرسائل الأقدم من {days} يوم...")
    
    try:
        # جلب جميع الرسائل
        all_data = collection.get()
        
        if not all_data or not all_data['ids']:
            logger.info("ℹ️ لا توجد رسائل في قاعدة البيانات")
            return 0
        
        # حساب التاريخ الحدي
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        ids_to_delete = []
        
        # فحص كل رسالة
        for i, metadata in enumerate(all_data['metadatas']):
            if 'date' in metadata and metadata['date']:
                try:
                    msg_date = datetime.fromisoformat(metadata['date'])
                    if msg_date < cutoff_date:
                        ids_to_delete.append(all_data['ids'][i])
                except Exception as e:
                    logger.debug(f"خطأ في قراءة التاريخ: {e}")
        
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(f"✅ تم حذف {len(ids_to_delete)} رسالة قديمة")
            return len(ids_to_delete)
        else:
            logger.info("ℹ️ لا توجد رسائل قديمة لحذفها")
            return 0
    
    except Exception as e:
        logger.error(f"❌ خطأ في حذف الرسائل القديمة: {e}")
        return 0
