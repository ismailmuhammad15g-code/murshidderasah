# vector_store.py
import os
import logging
import time
import google.generativeai as genai
from config import Config

# --- الإعدادات الأساسية ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
EMBED_MODEL = "models/text-embedding-004"
PINECONE_INDEX_NAME = "murshidderasah"

# --- دعم مفاتيح Google متعددة ---
GOOGLE_API_KEYS = Config.GOOGLE_API_KEYS
_current_key_index = 0

def _get_next_api_key():
    """اختيار المفتاح التالي بشكل دائري (Round Robin)"""
    global _current_key_index
    key = GOOGLE_API_KEYS[_current_key_index]
    _current_key_index = (_current_key_index + 1) % len(GOOGLE_API_KEYS)
    return key

logger.info(f"✅ تم تحميل {len(GOOGLE_API_KEYS)} مفتاح Google API")

# --- تهيئة نموذج جوجل (لإنشاء المتجهات) ---
try:
    # استخدام أول مفتاح جوجل متاح لإعداد النموذج
    first_google_key = next(key for key in Config.GOOGLE_API_KEYS if key and key != "NO_API_KEY")
    genai.configure(api_key=first_google_key)
    logger.info("✅ تم إعداد نموذج Google Embedding بنجاح.")
except StopIteration:
    logger.warning("⚠️ لم يتم العثور على مفتاح Google API صالح في الإعدادات.")
except Exception as e:
    logger.warning(f"⚠️ خطأ في إعداد Google AI: {e}")

# --- تهيئة الاتصال بـ Pinecone (الخادم) ---
pinecone_index = None

try:
    from pinecone import Pinecone
    
    # التحقق من وجود الإعدادات
    if Config.PINECONE_API_KEY and Config.PINECONE_HOST:
        pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        
        # التأكد من أن الـ Host URL لا يحتوي على "https://"
        host_url = Config.PINECONE_HOST.replace("https://", "")
        
        pinecone_index = pc.Index(host=host_url)
        stats = pinecone_index.describe_index_stats()
        logger.info(f"✅ تم الاتصال بـ Pinecone بنجاح. عدد المتجهات الحالي: {stats.get('total_vector_count', 0)}")
    else:
        logger.warning("⚠️ إعدادات Pinecone غير موجودة. سيتم العمل بدون vector store.")
except Exception as e:
    logger.error(f"❌ فشل الاتصال بـ Pinecone: {e}")
    logger.warning("⚠️ سيتم العمل بدون vector store.")
    pinecone_index = None


def get_embedding(text: str, task_type: str) -> list:
    """
    دالة مساعدة لتحويل النص إلى متجه (768 بُعد)
    task_type: "RETRIEVAL_DOCUMENT" (للتخزين) أو "RETRIEVAL_QUERY" (للبحث)
    """
    if not text or text.isspace():
        return []
    
    # 🔥 اختيار المفتاح التالي بشكل دائري
    api_key = _get_next_api_key()
    
    try:
        genai.configure(api_key=api_key)
        result = genai.embed_content(
            model=EMBED_MODEL,
            content=text,
            task_type=task_type
        )
        return result["embedding"]
    except Exception as e:
        error_msg = str(e)
        # معالجة خطأ 429 (Rate Limit)
        if "429" in error_msg or "quota" in error_msg.lower():
            logger.warning(f"⚠️ تم الوصول لحد المفتاح. الانتقال للمفتاح التالي...")
            if len(GOOGLE_API_KEYS) > 1:
                return get_embedding(text, task_type)  # محاولة أخرى
            else:
                logger.error("⏳ لدينا مفتاح واحد فقط. سيتم الانتظار 65 ثانية...")
                time.sleep(65)
                return get_embedding(text, task_type)
        logger.error(f"❌ فشل في إنشاء متجه: {error_msg}")
        return []


def add_to_db(text_to_add: str, document_id: str):
    """
    إضافة نص (ومعرفه) إلى قاعدة بيانات Pinecone السحابية
    """
    logger.info(f"⏳ جارِ إضافة المستند: {document_id}")
    
    # 1. إنشاء المتجه (للتخزين)
    embedding = get_embedding(text_to_add, task_type="RETRIEVAL_DOCUMENT")
    if not embedding:
        logger.warning(f"لم يتم إضافة المستند {document_id} بسبب فشل إنشاء المتجه.")
        return

    # 2. تجهيز الكائن للتخزين
    # Pinecone يخزن النص الأصلي في 'metadata'
    vector_to_upsert = {
        "id": document_id,
        "values": embedding,
        "metadata": {"original_text": text_to_add}
    }
    
    # 3. الإرسال إلى الخادم (upsert تعني إضافة أو تحديث)
    try:
        pinecone_index.upsert(vectors=[vector_to_upsert])
        logger.info(f"✅ تم إضافة/تحديث المستند: {document_id}")
    except Exception as e:
        logger.error(f"❌ فشل في رفع المتجه إلى Pinecone: {e}")


def query_db(question_text: str, top_k: int = 5) -> list:
    """
    البحث في قاعدة بيانات Pinecone عن أقرب النصوص للسؤال
    """
    logger.info(f"🔍 جارِ البحث عن: {question_text[:30]}...")
    
    # 1. إنشاء متجه السؤال (للبحث)
    query_embedding = get_embedding(question_text, task_type="RETRIEVAL_QUERY")
    if not query_embedding:
        logger.error("فشل البحث بسبب عدم القدرة على إنشاء متجه للسؤال.")
        return []

    # 2. البحث في Pinecone
    try:
        results = pinecone_index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True  # !! هذا أهم سطر، ليقوم بإرجاع النص الأصلي
        )
    except Exception as e:
        logger.error(f"❌ فشل في البحث في Pinecone: {e}")
        return []

    # 3. استخراج النصوص من النتائج
    context_texts = []
    for match in results.get('matches', []):
        if match.get('score', 0) > 0.7:  # (يمكنك تعديل درجة الثقة)
            text = match.get('metadata', {}).get('original_text')
            if text:
                context_texts.append(text)
                logger.info(f"  ... نتيجة مطابقة (Score: {match.get('score', 0):.2f})")
    
    logger.info(f"✅ تم العثور على {len(context_texts)} نتيجة مطابقة.")
    return context_texts


def build_database(documents: list):
    """بناء قاعدة بيانات Pinecone مع Batch Processing للسرعة القصوى"""
    num_keys = len(GOOGLE_API_KEYS)
    logger.info(f"🏛️ بدء بناء قاعدة بيانات Pinecone لـ {len(documents)} رسالة...")
    logger.info(f"🔥 استخدام {num_keys} مفتاح - سرعة {num_keys}x")
    
    BATCH_SIZE = 40
    total_docs = len(documents)
    total_batches = (total_docs + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, total_docs, BATCH_SIZE):
        batch_documents = documents[i: i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info(f"🔄 معالجة الدفعة {batch_num}/{total_batches} ({len(batch_documents)} رسالة)...")

        # فلترة المستندات الصالحة
        docs_to_process = [doc for doc in batch_documents if doc.get('text') and not doc['text'].isspace()]
        
        if not docs_to_process:
            logger.info("⚠️ لا توجد رسائل صالحة في هذه الدفعة")
            continue
        
        batch_texts = [doc['text'] for doc in docs_to_process]
        
        try:
            # اختيار المفتاح الدائري
            key_index = (batch_num - 1) % num_keys
            api_key = GOOGLE_API_KEYS[key_index]
            genai.configure(api_key=api_key)
            
            # إنشاء embeddings للدفعة كاملة
            result = genai.embed_content(
                model=EMBED_MODEL,
                content=batch_texts,
                task_type="RETRIEVAL_DOCUMENT"
            )
            
            embeddings = result['embedding']
            
            if len(embeddings) != len(batch_texts):
                logger.warning(f"⚠️ عدم تطابق: {len(embeddings)} embeddings vs {len(batch_texts)} texts")
                continue
            
            # تحضير المتجهات للرفع إلى Pinecone
            vectors_to_upsert = [
                {
                    "id": doc.get('id', f"doc_{i}_{j}"),
                    "values": embeddings[j],
                    "metadata": {
                        "original_text": doc['text'],
                        "link": doc.get('link', ''),
                        "date": doc.get('date', ''),
                        "type": doc.get('type', 'admin'),
                        "source_tag": doc.get('source_tag', 'public_channel')
                    }
                }
                for j, doc in enumerate(docs_to_process)
            ]
            
            # رفع الدفعة إلى Pinecone
            pinecone_index.upsert(vectors=vectors_to_upsert)
            logger.info(f"✅ تمت إضافة {len(embeddings)} رسالة إلى Pinecone")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ فشل معالجة الدفعة {batch_num}: {error_msg}")
            
            if "429" in error_msg or "quota" in error_msg.lower():
                logger.warning(f"⏳ Rate Limit. الانتظار 65 ثانية...")
                time.sleep(65)
                continue
        
        # الانتظار بعد كل دورة كاملة
        if i + BATCH_SIZE < total_docs:
            if batch_num % num_keys == 0:
                logger.warning(f"⏳ اكتملت دورة كاملة ({num_keys} دفعات). الانتظار 65 ثانية...")
                time.sleep(65)

    logger.info(f"🎉 اكتمل بناء قاعدة البيانات! تم معالجة {total_docs} رسالة.")


def search_database(query_text: str, top_k: int = 5):
    """بحث ذكي مع فلترة Pinecone (يدعم البحث بالمصدر والنوع)"""
    logger.info(f"🔍 بدء البحث في Pinecone عن: {query_text[:50]}...")
    
    # إنشاء متجه السؤال
    query_embedding = get_embedding(query_text, task_type="RETRIEVAL_QUERY")
    if not query_embedding:
        logger.error("فشل البحث بسبب عدم القدرة على إنشاء متجه للسؤال")
        return []
    
    all_results = []
    
    try:
        # البحث العام (بدون فلترة)
        results = pinecone_index.query(
            vector=query_embedding,
            top_k=top_k * 2,  # نأخذ أكثر للتنويع
            include_metadata=True
        )
        
        for match in results.get('matches', []):
            if match.get('score', 0) > 0.7:
                metadata = match.get('metadata', {})
                text = metadata.get('original_text')
                if text:
                    all_results.append({
                        "text": text,
                        "link": metadata.get('link', ''),
                        "type": metadata.get('type', 'admin'),
                        "source_tag": metadata.get('source_tag', 'public_channel'),
                        "score": match.get('score', 0)
                    })
        
        logger.info(f"✅ تم العثور على {len(all_results)} نتيجة")
        return all_results[:top_k]  # نرجع فقط العدد المطلوب
        
    except Exception as e:
        logger.error(f"❌ فشل البحث في Pinecone: {e}")
        return []


def add_new_messages(documents: list):
    """إضافة رسائل جديدة إلى Pinecone (للتحديث الآلي كل 5 دقائق)"""
    if not documents:
        return 0
    
    logger.info(f"🔄 محاولة إضافة {len(documents)} رسالة جديدة إلى Pinecone...")
    
    # استخدام build_database لأنه يدعم Batch Processing
    try:
        build_database(documents)
        logger.info(f"✅ تمت إضافة الرسائل الجديدة بنجاح")
        return len(documents)
    except Exception as e:
        logger.error(f"❌ خطأ في إضافة الرسائل: {e}")
        return 0


def delete_old_messages(days: int = 365):
    """حذف رسائل قديمة من Pinecone (ملاحظة: يتطلب جلب كل المتجهات)"""
    logger.info(f"🧹 حذف الرسائل الأقدم من {days} يوم غير متاح حالياً في Pinecone Serverless")
    # Pinecone Serverless لا يدعم query للحذف بناءً على metadata مباشرة
    # يجب استخدام list() لجلب كل IDs ثم فلترتها وحذفها
    return 0
