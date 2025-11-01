"""
===================================
vector_store.py - قاعدة بيانات المتجهات باستخدام FAISS
===================================

النسخة 3.1 - FAISS بدلاً من ChromaDB
- أخف 100 مرة (50 MB بدلاً من 500 MB)
- أسرع في البحث
- لا يحتاج مساحة تخزين ضخمة
"""

import google.generativeai as genai
import numpy as np
import faiss
import json
import logging
import time
import os
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===================================
# الإعدادات
# ===================================

GOOGLE_API_KEYS = Config.GOOGLE_API_KEYS
EMBEDDING_MODEL = Config.GEMINI_EMBED_MODEL
EMBEDDING_DIM = 768  # حجم متجه Gemini Embedding

# ملفات قاعدة البيانات
FAISS_INDEX_FILE = "database.faiss"
METADATA_FILE = "metadata.json"

# متغير لتتبع المفتاح الحالي (Round Robin)
_current_key_index = 0

logger.info(f"✅ تم تحميل {len(GOOGLE_API_KEYS)} مفتاح Google API")

# ===================================
# وظائف المفاتيح (Round Robin)
# ===================================

def _get_next_api_key():
    """اختيار المفتاح التالي بشكل دائري"""
    global _current_key_index
    key = GOOGLE_API_KEYS[_current_key_index]
    _current_key_index = (_current_key_index + 1) % len(GOOGLE_API_KEYS)
    return key

def _get_embedding_with_retry(text, max_retries=3):
    """
    الحصول على متجه التضمين (Embedding) مع إعادة المحاولة
    يدور عبر المفاتيح المتعددة عند الفشل
    """
    for attempt in range(max_retries):
        try:
            # اختيار المفتاح التالي
            api_key = _get_next_api_key()
            genai.configure(api_key=api_key)
            
            # الحصول على Embedding
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document"
            )
            
            return np.array(result['embedding'], dtype='float32')
            
        except Exception as e:
            logger.warning(f"⚠️ محاولة {attempt + 1}/{max_retries} فشلت: {str(e)[:100]}")
            
            # إذا كان الخطأ بسبب الحصة (quota)، جرب المفتاح التالي فوراً
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                logger.info("🔄 تبديل للمفتاح التالي...")
                time.sleep(1)
                continue
            
            # خطأ آخر - انتظر قبل إعادة المحاولة
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    raise Exception(f"❌ فشل الحصول على embedding بعد {max_retries} محاولات")

# ===================================
# بناء قاعدة البيانات
# ===================================

def build_database(documents):
    """
    بناء قاعدة بيانات FAISS من قائمة المستندات
    
    Args:
        documents: قائمة من القواميس، كل قاموس يحتوي على:
            - text: النص
            - link: الرابط
            - type: النوع ('admin' أو 'student')
    
    Returns:
        bool: True إذا نجح البناء
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 بدء بناء قاعدة البيانات باستخدام FAISS")
        logger.info(f"📊 عدد المستندات: {len(documents)}")
        logger.info("=" * 60)
        
        # التحقق من وجود مستندات
        if not documents:
            logger.error("❌ لا توجد مستندات لبناء قاعدة البيانات")
            return False
        
        # إنشاء فهرس FAISS
        index = faiss.IndexFlatL2(EMBEDDING_DIM)  # L2 distance
        
        # قائمة البيانات الوصفية
        metadata_list = []
        
        # معالجة كل مستند
        successful = 0
        failed = 0
        
        for i, doc in enumerate(documents):
            try:
                # التقدم
                if (i + 1) % 100 == 0:
                    logger.info(f"⏳ معالجة: {i + 1}/{len(documents)} ({(i+1)*100/len(documents):.1f}%)")
                
                # الحصول على Embedding
                text = doc.get('text', '')
                if not text:
                    failed += 1
                    continue
                
                embedding = _get_embedding_with_retry(text)
                
                # إضافة إلى الفهرس
                index.add(np.array([embedding]))
                
                # حفظ البيانات الوصفية
                metadata_list.append({
                    'id': i,
                    'text': text,
                    'link': doc.get('link', ''),
                    'type': doc.get('type', 'student'),
                    'date': doc.get('date', '')
                })
                
                successful += 1
                
                # انتظار صغير لتجنب تجاوز الحصة
                if (i + 1) % 10 == 0:
                    time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ خطأ في معالجة المستند {i}: {str(e)[:100]}")
                failed += 1
                continue
        
        # حفظ الفهرس
        logger.info("💾 حفظ فهرس FAISS...")
        faiss.write_index(index, FAISS_INDEX_FILE)
        
        # حفظ البيانات الوصفية
        logger.info("💾 حفظ البيانات الوصفية...")
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata_list, f, ensure_ascii=False, indent=2)
        
        # الإحصائيات
        logger.info("=" * 60)
        logger.info("✅ اكتمل بناء قاعدة البيانات!")
        logger.info(f"📊 المستندات الناجحة: {successful}")
        logger.info(f"❌ المستندات الفاشلة: {failed}")
        logger.info(f"💾 حجم الفهرس: {os.path.getsize(FAISS_INDEX_FILE) / 1024 / 1024:.2f} MB")
        logger.info(f"💾 حجم البيانات: {os.path.getsize(METADATA_FILE) / 1024 / 1024:.2f} MB")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ فادح في بناء قاعدة البيانات: {e}")
        logger.exception(e)
        return False

# ===================================
# البحث في قاعدة البيانات
# ===================================

def search_database(query_text, top_k=10):
    """
    البحث في قاعدة البيانات عن أقرب النتائج
    
    Args:
        query_text: نص الاستعلام
        top_k: عدد النتائج المطلوبة
    
    Returns:
        list: قائمة من القواميس تحتوي على النتائج
    """
    try:
        # التحقق من وجود الملفات
        if not os.path.exists(FAISS_INDEX_FILE):
            logger.error(f"❌ لم يتم العثور على ملف الفهرس: {FAISS_INDEX_FILE}")
            logger.error("💡 يجب بناء قاعدة البيانات أولاً: python rebuild_database.py")
            return []
        
        if not os.path.exists(METADATA_FILE):
            logger.error(f"❌ لم يتم العثور على ملف البيانات: {METADATA_FILE}")
            return []
        
        # تحميل الفهرس
        index = faiss.read_index(FAISS_INDEX_FILE)
        
        # تحميل البيانات الوصفية
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
        
        # الحصول على embedding للاستعلام
        query_embedding = _get_embedding_with_retry(query_text)
        
        # البحث في الفهرس
        distances, indices = index.search(np.array([query_embedding]), top_k)
        
        # جمع النتائج
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(metadata_list):
                result = metadata_list[idx].copy()
                result['distance'] = float(distances[0][i])
                result['rank'] = i + 1
                results.append(result)
        
        logger.info(f"🔍 تم العثور على {len(results)} نتيجة للاستعلام")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ خطأ في البحث: {e}")
        logger.exception(e)
        return []

# ===================================
# البحث الهجين (Admin + Student)
# ===================================

def hybrid_search(query_text, admin_results=7, student_results=7):
    """
    بحث هجين: يجلب نتائج منفصلة من admin و student
    
    Args:
        query_text: نص الاستعلام
        admin_results: عدد نتائج admin
        student_results: عدد نتائج student
    
    Returns:
        list: قائمة مدمجة من النتائج
    """
    try:
        # البحث عن نتائج أكثر لنتمكن من الفلترة
        all_results = search_database(query_text, top_k=50)
        
        # فصل النتائج حسب النوع
        admin_list = [r for r in all_results if r.get('type') == 'admin']
        student_list = [r for r in all_results if r.get('type') == 'student']
        
        # أخذ العدد المطلوب
        final_results = []
        final_results.extend(admin_list[:admin_results])
        final_results.extend(student_list[:student_results])
        
        # ترتيب حسب المسافة
        final_results.sort(key=lambda x: x.get('distance', 999))
        
        logger.info(f"🎯 نتائج هجينة: {len(admin_list[:admin_results])} admin + {len(student_list[:student_results])} student")
        
        return final_results
        
    except Exception as e:
        logger.error(f"❌ خطأ في البحث الهجين: {e}")
        return []

# ===================================
# وظائف مساعدة
# ===================================

def add_messages_to_db(messages):
    """
    إضافة رسائل جديدة إلى قاعدة البيانات الموجودة
    
    ملاحظة: FAISS لا يدعم الإضافة التدريجية بكفاءة
    لذلك، يجب إعادة بناء القاعدة بالكامل
    """
    logger.warning("⚠️ FAISS لا يدعم الإضافة التدريجية")
    logger.info("💡 لإضافة رسائل جديدة، استخدم: python rebuild_database.py")
    return False

def get_database_stats():
    """الحصول على إحصائيات قاعدة البيانات"""
    try:
        if not os.path.exists(FAISS_INDEX_FILE) or not os.path.exists(METADATA_FILE):
            return {
                'exists': False,
                'message': 'قاعدة البيانات غير موجودة'
            }
        
        # تحميل البيانات
        index = faiss.read_index(FAISS_INDEX_FILE)
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
        
        # حساب الإحصائيات
        admin_count = sum(1 for m in metadata_list if m.get('type') == 'admin')
        student_count = sum(1 for m in metadata_list if m.get('type') == 'student')
        
        return {
            'exists': True,
            'total_documents': len(metadata_list),
            'admin_documents': admin_count,
            'student_documents': student_count,
            'index_size_mb': os.path.getsize(FAISS_INDEX_FILE) / 1024 / 1024,
            'metadata_size_mb': os.path.getsize(METADATA_FILE) / 1024 / 1024
        }
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الإحصائيات: {e}")
        return {
            'exists': False,
            'error': str(e)
        }

# ===================================
# التهيئة
# ===================================

logger.info("✅ تم تحميل vector_store.py (FAISS النسخة)")
