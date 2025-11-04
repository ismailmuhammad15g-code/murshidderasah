# vector_store.py - نسخة مبسطة لـ Railway
import os
import logging
import google.generativeai as genai
from config import Config

logger = logging.getLogger(__name__)
EMBED_MODEL = "models/text-embedding-004"
pinecone_index = None

# --- تهيئة نموذج جوجل (لإنشاء المتجهات) ---
try:
    first_google_key = next(key for key in Config.GOOGLE_API_KEYS if key and key != "NO_API_KEY")
    genai.configure(api_key=first_google_key)
    logger.info("✅ (vector_store) تم إعداد نموذج Google Embedding.")
except StopIteration:
    logger.error("❌ (vector_store) لم يتم العثور على مفتاح Google API صالح.")

# --- تهيئة الاتصال بـ Pinecone (الخادم) ---
try:
    from pinecone import Pinecone
    
    if Config.PINECONE_API_KEY and Config.PINECONE_HOST:
        pc = Pinecone(api_key=Config.PINECONE_API_KEY)
        host_url = Config.PINECONE_HOST.replace("https://", "")
        pinecone_index = pc.Index(host=host_url)
        stats = pinecone_index.describe_index_stats()
        logger.info(f"✅ (vector_store) تم الاتصال بـ Pinecone. عدد المتجهات: {stats.get('total_vector_count', 0)}")
    else:
        logger.warning("⚠️ (vector_store) متغيرات Pinecone غير موجودة. سيعمل بدون RAG.")
except Exception as e:
    logger.error(f"❌ (vector_store) فشل الاتصال بـ Pinecone: {e}")
    pinecone_index = None

def get_embedding(text: str, task_type: str):
    """دالة مساعدة لتحويل النص إلى متجه (768 بُعد)"""
    if not text or text.isspace():
        return []
    try:
        result = genai.embed_content(
            model=EMBED_MODEL,
            content=text,
            task_type=task_type
        )
        return result["embedding"]
    except Exception as e:
        logger.error(f"❌ (vector_store) فشل في إنشاء متجه: {e}")
        return []

def add_to_db(text_to_add: str, document_id: str):
    """إضافة نص إلى قاعدة بيانات Pinecone السحابية"""
    if not pinecone_index:
        return
    
    logger.info(f"⏳ (vector_store) جارٍ إضافة المستند: {document_id}")
    embedding = get_embedding(text_to_add, task_type="RETRIEVAL_DOCUMENT")
    if not embedding:
        return

    vector_to_upsert = {
        "id": document_id,
        "values": embedding,
        "metadata": {"original_text": text_to_add}
    }
    
    try:
        pinecone_index.upsert(vectors=[vector_to_upsert])
        logger.info(f"✅ (vector_store) تم إضافة/تحديث المستند: {document_id}")
    except Exception as e:
        logger.error(f"❌ (vector_store) فشل في رفع المتجه إلى Pinecone: {e}")

def query_db(question_text: str, top_k: int = 5):
    """البحث في قاعدة بيانات Pinecone عن أقرب النصوص للسؤال"""
    if not pinecone_index:
        return []
    
    logger.info(f"🔍 (vector_store) جارٍ البحث عن: {question_text[:30]}...")
    query_embedding = get_embedding(question_text, task_type="RETRIEVAL_QUERY")
    if not query_embedding:
        return []

    try:
        results = pinecone_index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
    except Exception as e:
        logger.error(f"❌ (vector_store) فشل في البحث في Pinecone: {e}")
        return []

    context_texts = []
    for match in results.get('matches', []):
        if match.get('score', 0) > 0.7:
            text = match.get('metadata', {}).get('original_text')
            if text:
                context_texts.append(text)
    
    logger.info(f"✅ (vector_store) تم العثور على {len(context_texts)} نتيجة مطابقة.")
    return context_texts
