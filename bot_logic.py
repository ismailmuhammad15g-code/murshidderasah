# bot_logic.py
"""
منطق البوت والذكاء الاصطناعي المشترك بين التليجرام والموقع
"""

import logging
from config import Config
import vector_store
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes

# الإعداد
logger = logging.getLogger(__name__)

# إعداد نماذج Gemini (باستخدام الـ 10 مفاتيح للتوزيع)
chat_models = []
chat_model_counter = 0

def init_gemini_models():
    """إعداد نماذج Gemini من المفاتيح المتاحة"""
    global chat_models
    
    if chat_models:  # إذا تم الإعداد مسبقاً
        return
    
    for api_key in Config.GOOGLE_API_KEYS:
        if api_key and api_key != "NO_API_KEY":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(Config.GEMINI_CHAT_MODEL)
            chat_models.append(model)
    
    logger.info(f"✅ تم إعداد {len(chat_models)} نموذج Gemini للدردشة")


def get_next_chat_model():
    """الحصول على النموذج التالي بطريقة دائرية"""
    global chat_model_counter
    
    if not chat_models:
        init_gemini_models()
    
    if not chat_models:
        raise Exception("لا يوجد نماذج Gemini متاحة")
    
    current_model = chat_models[chat_model_counter % len(chat_models)]
    chat_model_counter += 1
    return current_model


async def get_smart_reply(question: str) -> dict:
    """
    الدالة الذكية الرئيسية - تستخدمها التليجرام والموقع
    
    Args:
        question: سؤال المستخدم
    
    Returns:
        dict: {"answer": str, "links": list}
    """
    logger.info(f"🤔 استفسار جديد: {question[:50]}...")
    
    # 1. البحث الهجين الذكي (من vector_store.py)
    evidence_list = vector_store.search_database(question)
    
    if not evidence_list:
        return {
            "answer": "أهلاً بك! 👋 بحثت لك في سجلات القناة، لكن لم أجد معلومة واضحة بخصوص هذا الموضوع. 🔍\n\n"
                     "💡 نصيحة: حاول إعادة صياغة السؤال أو استخدام كلمات مفتاحية أخرى.",
            "links": []
        }
    
    # 2. بناء البرومبت الودود والمحلل
    evidence_context = ""
    for i, ev in enumerate(evidence_list, 1):
        doc_type = ev.get('type', 'unknown')
        source_tag = ev.get('source_tag', 'public_channel')
        
        # إضافة معلومات المصدر
        source_info = ""
        if source_tag == "accommodations":
            source_info = " [جروب الإقامات]"
        elif doc_type == "admin":
            source_info = " [منشور رسمي]"
        elif doc_type == "student":
            source_info = " [نقاش طلاب]"
        
        evidence_context += f"--- دليل {i}{source_info} (الرابط: {ev['link']}) ---\n{ev['text']}\n\n"
    
    final_prompt = f"""أنت "مرشد الدراسة"، مساعد ذكي وودود مُتخصص في مساعدة طلاب المعاهد الأزهرية. 📚

مهمتك هي الإجابة على سؤال الطالب بناءً على الأدلة المُرفقة من القناة الرسمية والمصادر الموثوقة.

🎯 **قواعد الإجابة:**

1. **التحليل الشامل**: اقرأ جميع الأدلة بعناية، واجمع المعلومات من مصادر متعددة
2. **الوضوح والتنظيم**: قسّم الإجابة إلى نقاط واضحة إذا كان الموضوع معقداً
3. **الاقتباس الدقيق**: عند نقل معلومة رسمية، ضع اقتباساً مباشراً بين علامتي "..."
4. **السياق الكامل**: اذكر التفاصيل المهمة (تواريخ، شروط، خطوات)
5. **النبرة الودودة**: استخدم الإيموجي بذكاء، وكن مشجعاً وداعماً
6. **الأمانة**: إذا لم تجد إجابة واضحة، أو كانت المعلومة غير كافية، قل ذلك صراحة

---

**سؤال الطالب:**
{question}

---

**الأدلة المتوفرة:**
{evidence_context}

---

**إجابتك** (ودية، محللة، مع اقتباس منسق إذا لزم):
"""
    
    try:
        # 3. اختيار المفتاح والرد
        chat_model = get_next_chat_model()
        response = chat_model.generate_content(final_prompt)
        
        # 4. إرجاع الرد والأدلة
        links = [ev['link'] for ev in evidence_list]
        unique_links = list(dict.fromkeys(links))  # إزالة التكرار
        
        return {
            "answer": response.text,
            "links": unique_links[:5]  # أفضل 5 روابط
        }
        
    except Exception as e:
        logger.error(f"❌ خطأ في توليد الرد: {e}")
        return {
            "answer": f"عذراً، حدث خطأ أثناء معالجة سؤالك. 😔\n\n"
                     f"يمكنك مراجعة المصادر التالية مباشرة للحصول على المعلومة.",
            "links": [ev['link'] for ev in evidence_list][:5]
        }


# ========================================
# دوال التليجرام البوت
# ========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب مع زر الـ WebApp"""
    
    website_url = Config.WEBHOOK_URL.replace('/webhook', '') if Config.WEBHOOK_URL else "https://your-app.pythonanywhere.com"
    
    keyboard = [
        [
            KeyboardButton(
                "🚀 فتح البوابة (المكتبة والاستفسار)",
                web_app=WebAppInfo(url=website_url)
            )
        ],
        [
            KeyboardButton("📊 آخر 5 أخبار رسمية")
        ]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_message = """مرحباً بك في **مرشد الدراسة**! 👋

🤖 **يمكنك:**
• طرح أي سؤال هنا مباشرة
• فتح البوابة للوصول للمكتبة والاستفسار الذكي
• الاطلاع على آخر الأخبار الرسمية

💡 **نصيحة:** اكتب سؤالك بوضوح، وسأبحث لك في آلاف الرسائل!"""
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_latest_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر 5 أخبار رسمية"""
    
    try:
        # البحث عن أحدث منشورات الأدمن
        vector_store._init_chromadb()
        
        # استعلام للحصول على آخر الأخبار
        recent_news = vector_store.collection.query(
            query_embeddings=None,
            where={"type": "admin"},
            n_results=5
        )
        
        if not recent_news or not recent_news['metadatas'] or not recent_news['metadatas'][0]:
            await update.message.reply_text("لا توجد أخبار رسمية حالياً. 🔍")
            return
        
        news_text = "📊 **آخر 5 أخبار رسمية:**\n\n"
        
        for i, meta in enumerate(recent_news['metadatas'][0], 1):
            text_preview = meta['text'][:100] + "..." if len(meta['text']) > 100 else meta['text']
            news_text += f"{i}. {text_preview}\n🔗 {meta['link']}\n\n"
        
        await update.message.reply_text(
            news_text,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الأخبار: {e}")
        await update.message.reply_text("عذراً، حدث خطأ أثناء جلب الأخبار. 😔")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية للبوت"""
    
    text = update.message.text
    
    if not text:
        return
    
    # التعامل مع الأزرار الخاصة
    if text == "📊 آخر 5 أخبار رسمية":
        await handle_latest_news(update, context)
        return
    
    # الاستفسار الذكي
    await update.message.reply_text(
        "أهلاً بك! 👋\nلحظات... أقوم بالبحث لك في السجلات... 🕵️‍♂️"
    )
    
    # استدعاء الدالة المشتركة
    reply_data = await get_smart_reply(text)
    
    # بناء رسالة الرد
    response_text = reply_data["answer"]
    
    # إضافة المصادر في النهاية
    if reply_data["links"]:
        evidence_footer = "\n\n━━━━━━━━━━━━━━━━\n📚 **المصادر:**\n"
        for i, link in enumerate(reply_data["links"], 1):
            evidence_footer += f"{i}. {link}\n"
        response_text += evidence_footer
    
    # إرسال الرد (مع تقسيم إذا كان طويلاً)
    if len(response_text) > 4000:
        # تقسيم الرسالة
        parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
        for part in parts:
            await update.message.reply_text(
                part,
                disable_web_page_preview=True,
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            response_text,
            disable_web_page_preview=True,
            parse_mode='Markdown'
        )


# تهيئة النماذج عند الاستيراد
init_gemini_models()
