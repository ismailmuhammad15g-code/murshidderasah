# bot_logic.py
"""
منطق البوت والذكاء الاصطناعي المشترك بين التليجرام والموقع
"""

import logging
from config import Config
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
import vector_store  # لاستخدام RAG

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
    الدالة الذكية الرئيسية - مع تفعيل RAG (البحث في vector store)
    
    Args:
        question: سؤال المستخدم
    
    Returns:
        dict: {"answer": str, "links": list}
    """
    logger.info(f"🤔 استفسار جديد: {question[:50]}...")
    
    try:
        # 1. البحث في vector store (حتى لو فارغ، سيرجع [])
        search_results = vector_store.query_db(question, top_k=5)
        
        # 2. بناء البرومبت مع السياق (إن وُجد)
        if search_results:
            context = "\n\n".join([
                f"نتيجة {i+1}:\n{result['text']}\n(المصدر: {result.get('message_id', 'غير محدد')})"
                for i, result in enumerate(search_results)
            ])
            
            final_prompt = f"""أنت "مرشد الدراسة"، مساعد ذكي وودود مُتخصص في مساعدة طلاب المعاهد الأزهرية. 📚

لديك معلومات من القناة الرسمية لمساعدتك:

**المعلومات المتاحة:**
{context}

**سؤال الطالب:**
{question}

**تعليماتك:**
- استخدم المعلومات أعلاه للإجابة إن كانت ذات صلة
- إذا لم تجد إجابة في المعلومات، أجِب بناءً على معرفتك
- كُن ودياً وواضحاً ومفيداً
- استخدم الإيموجي بذكاء ✨

**إجابتك:**
"""
            
            # جمع روابط المصادر
            links = [result.get('link', '') for result in search_results if result.get('link')]
        else:
            # لا توجد نتائج - رد عادي
            final_prompt = f"""أنت "مرشد الدراسة"، مساعد ذكي وودود مُتخصص في مساعدة طلاب المعاهد الأزهرية. 📚

أجب على السؤال التالي بطريقة ودية ومفيدة:

**السؤال:**
{question}

**إجابتك** (ودية، واضحة، مع استخدام الإيموجي بذكاء):
"""
            links = []
        
        # 3. توليد الرد
        chat_model = get_next_chat_model()
        response = chat_model.generate_content(final_prompt)
        
        return {
            "answer": response.text,
            "links": links
        }
        
    except Exception as e:
        logger.error(f"❌ خطأ في توليد الرد: {e}")
        logger.exception(e)
        return {
            "answer": "عذراً، حدث خطأ أثناء معالجة سؤالك. 😔\n\nيرجى المحاولة مرة أخرى لاحقاً.",
            "links": []
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
    """عرض رسالة بديلة - الميزة غير متاحة حاليًا"""
    await update.message.reply_text(
        "📊 هذه الميزة قيد التطوير حالياً. 🔧\n\n"
        "يمكنك زيارة القناة الرسمية مباشرة للاطلاع على آخر الأخبار."
    )


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
