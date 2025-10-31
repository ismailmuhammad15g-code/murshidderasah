# web_search.py
"""
V2: الخطة البديلة - البحث في موقع الأزهر الرسمي عند فشل البحث في تليجرام
"""
import httpx
from bs4 import BeautifulSoup
from googlesearch import search
import asyncio
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_page_content(url: str) -> str:
    """
    يسحب محتوى صفحة ويب وينظفها
    
    Args:
        url: رابط الصفحة
    
    Returns:
        النص المستخرج من الصفحة (أول 1500 حرف)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True, timeout=10.0)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # تنظيف النص - استخراج النصوص من الفقرات
                paragraphs = soup.find_all(['p', 'div', 'span'])
                text = ' '.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
                
                # نأخذ أول 1500 حرف فقط لتجنب الإطالة
                return text[:1500] if text else None
            
            logger.warning(f"⚠️ فشل سحب الصفحة: {url} (Status: {response.status_code})")
            return None
    
    except Exception as e:
        logger.error(f"❌ فشل سحب صفحة الويب {url}: {e}")
        return None


async def search_azhar_website(query: str) -> str:
    """
    يبحث في موقع الأزهر الرسمي ويعيد نص أفضل 3 نتائج
    
    Args:
        query: سؤال المستخدم
    
    Returns:
        نص الأدلة من الموقع الرسمي (أو None إذا فشل)
    """
    logger.info(f"🌐 V2: بدء البحث في الويب عن: {query}...")
    
    # بناء استعلام البحث المحدد
    search_query = f"site:{Config.AZHAR_WEBSITE_URL} {query}"
    evidence_text = ""
    
    try:
        # استخدام مكتبة بحث جوجل
        # ملاحظة: هذه المكتبة blocking، لذا نستخدم run_in_executor
        loop = asyncio.get_event_loop()
        search_results = await loop.run_in_executor(
            None, 
            lambda: list(search(search_query, num_results=3, lang="ar", sleep_interval=2))
        )

        if not search_results:
            logger.warning("⚠️ لم يتم العثور على نتائج في موقع الأزهر")
            return None

        logger.info(f"✅ تم العثور على {len(search_results)} نتائج. سحب المحتوى...")

        # سحب محتوى الصفحات
        tasks = [fetch_page_content(url) for url in search_results]
        contents = await asyncio.gather(*tasks)

        # تجميع الأدلة
        for i, content in enumerate(contents):
            if content:
                evidence_text += f"--- دليل {i+1} (الرابط: {search_results[i]}) ---\n{content}\n\n"
        
        if evidence_text:
            logger.info(f"✅ تم استخراج {len(contents)} دليل من الويب")
            return evidence_text
        else:
            logger.warning("⚠️ لم يتم استخراج أي محتوى مفيد من الصفحات")
            return None

    except ImportError:
        logger.error("❌ مكتبة googlesearch-python غير مثبتة! قم بتشغيل: pip install googlesearch-python")
        return None
    except Exception as e:
        logger.error(f"❌ فشل البحث في الويب: {e}")
        return None
