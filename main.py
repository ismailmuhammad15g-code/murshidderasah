import logging
import sqlite3
import re
import os
import json
import string
import html
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram.constants import ChatAction
from config import Config
from database import *
from email_service import send_inquiry_email
from advanced_features import *
import scraper
import vector_store
import google.generativeai as genai

# === استيراد APScheduler للمهام الآلية ===
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# تهيئة السجل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("logs/bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# إعداد نماذج Gemini للدردشة (استخدام جميع المفاتيح - Round Robin)
try:
    # إنشاء قائمة من النماذج، واحد لكل مفتاح
    chat_models = [
        genai.GenerativeModel(Config.GEMINI_CHAT_MODEL)
        for _ in Config.GOOGLE_API_KEYS
    ]
    
    # تهيئة كل نموذج بمفتاحه
    for i, key in enumerate(Config.GOOGLE_API_KEYS):
        genai.configure(api_key=key)
    
    chat_model_counter = 0  # عداد لتتبع المفتاح الحالي
    logger.info(f"✅ تم إعداد {len(chat_models)} نموذج دردشة (للدوران على المفاتيح)")
except Exception as e:
    logger.error(f"❌ فشل إعداد Gemini: {e}")
    chat_models = []
    chat_model_counter = 0

# قاموس لتتبع حالة المستخدم (مهم جداً)
user_state = {}

# ============== دالة لحماية النصوص من أخطاء Markdown ==============

def escape_markdown(text):
    """حماية النصوص من أحرف Markdown الخاصة"""
    if not text:
        return text
    # الأحرف الخاصة في Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = str(text).replace(char, f'\\{char}')
    return text

# ============== أدوات أمان الملفات ==============

def sanitize_filename(name: str, default_ext: str = "") -> str:
    name = os.path.basename(name or "")
    # إزالة محارف غير صالحة
    allowed = string.ascii_letters + string.digits + "._- ()[]{}@!+&"
    cleaned = ''.join(ch if ch in allowed else '_' for ch in name)
    cleaned = cleaned.strip(' .')
    if not cleaned:
        cleaned = f"file{default_ext}"
    # الحد من الطول
    if len(cleaned) > 100:
        base, ext = os.path.splitext(cleaned)
        cleaned = base[:90] + ext
    return cleaned

def unique_path(dest_dir: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    candidate = os.path.join(dest_dir, filename)
    i = 1
    while os.path.exists(candidate):
        candidate = os.path.join(dest_dir, f"{base}_{i}{ext}")
        i += 1
    return candidate

# ============== القائمة الرئيسية ==============

# ============== دوال RAG الجديدة ==============

async def setup_database_once():
    """
    يفحص قاعدة البيانات ويبنيها إذا لم تكن موجودة + معالجة خطأ 0 رسالة.
    """
    db_file_path = os.path.join(Config.DB_PATH, "chroma.sqlite3")
    lite_path = os.path.join(Config.DB_PATH, "lite_store.json")
    
    # ✅ فحص قاعدة البيانات - مفعّل
    # ملاحظة: عطّل هذا السطر مؤقتاً فقط إذا أردت إكمال بناء غير مكتمل
    if os.path.exists(db_file_path) or os.path.exists(lite_path):
        logger.info("قاعدة البيانات موجودة بالفعل. سيتم تخطي البناء.")
        return True  # نجح

    logger.warning("قاعدة البيانات غير موجودة. سيتم البدء في البناء...")
    
    # --- هنا يبدأ الإصلاح ---
    documents = await scraper.scrape_channel()
    
    if documents is None:
        logger.critical("!!! فشل فادح في سحب الرسائل (خطأ في Telethon). تأكد من مفاتيح API_ID/HASH.")
        return False  # فشل
        
    if len(documents) == 0:
        logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.error("!!! خطأ: تم سحب 0 رسالة.")
        logger.error("!!! الحل 1: هل قمت بالانضمام لقناة @mahadalazhar بحسابك الشخصي؟")
        logger.error("!!! الحل 2: حاول حذف ملف 'anon.session' وإعادة التشغيل.")
        logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return False  # فشل
    # --- نهاية الإصلاح ---
        
    logger.info(f"تم سحب {len(documents)} رسالة. بدء بناء قاعدة المتجهات (قد يستغرق دقائق)...")
    vector_store.build_database(documents)
    logger.info("تم الانتهاء من إعداد قاعدة البيانات.")
    return True  # نجح

async def handle_latest_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج زر آخر 5 أخبار رسمية - سحب مباشر
    """
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)

    try:
        # نستدعي دالة جديدة من السكريبر
        latest_posts = await scraper.get_latest_admin_posts_live(count=5)

        if not latest_posts:
            await update.message.reply_text("لم أجد أي منشورات رسمية حديثة.")
            return

        response_text = "🔥 إليك آخر 5 أخبار رسمية من القناة:\n\n"
        for i, post in enumerate(latest_posts):
            # نأخذ أول 150 حرف من المنشور
            snippet = post['text'][:150] + "..." 
            response_text += f"**{i+1}. {post['date'].split('T')[0]}**\n"
            response_text += f"{snippet}\n"
            response_text += f"[اضغط هنا لقراءة المنشور كاملاً]({post['link']})\n\n"

        await update.message.reply_text(response_text, disable_web_page_preview=True, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"حدث خطأ أثناء جلب آخر الأخبار: {e}")
        await update.message.reply_text("عذراً، حدث خطأ أثناء الاتصال بالقناة.")

async def handle_smart_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يعالج الاستفسار الذكي (RAG) - مع ذكاء معزّز وشخصية ودودة
    """
    global chat_model_counter  # استدعاء العداد العالمي
    
    user_question = update.message.text
    user_name = update.effective_user.first_name or "عزيزي الطالب"
    chat_id = update.message.chat_id
    
    if not chat_models:
        await update.message.reply_text("عذراً، خدمة الذكاء الاصطناعي متوقفة حالياً.")
        return

    # رسالة انتظار ودودة
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING) 
    
    try:
        # البحث المعزز في قاعدة البيانات
        evidence_list = vector_store.search_database(user_question)
        
        # 🔄 اختيار النموذج التالي في الدور (Round Robin)
        current_model_index = chat_model_counter % len(chat_models)
        current_api_key = Config.GOOGLE_API_KEYS[current_model_index]
        
        # تهيئة genai بالمفتاح الحالي
        genai.configure(api_key=current_api_key)
        chat_model = chat_models[current_model_index]
        
        chat_model_counter += 1  # زيادة العداد للمرة القادمة
        logger.info(f"🔑 استخدام مفتاح الدردشة رقم {current_model_index + 1}/{len(chat_models)}")

        # إذا لم نجد أي أدلة، نستخدم نموذج إبداعي للمساعدة
        if not evidence_list:
            creative_prompt = f"""
            أنت مساعد ذكي ومفيد في بوت "مرشد الدراسة" لمدرسة الأزهر الإعدادية.
            
            سأل الطالب {user_name}: "{user_question}"
            
            لم أجد معلومات محددة حول هذا السؤال في سجلات القناة الرسمية الحديثة.
            
            مهمتك:
            1. قدم مساعدة عامة ومفيدة بناءً على السؤال
            2. اقترح كيف يمكن للطالب الحصول على إجابة دقيقة
            3. كن ودوداً ومشجعاً
            4. لا تختلق معلومات محددة عن المدرسة
            
            ابدأ ردك بـ "أهلاً {user_name}! 🌟"
            """
            
            response = chat_model.generate_content(creative_prompt)
            creative_answer = response.text
            
            await update.message.reply_text(
                creative_answer + "\n\n━━━━━━━━━━━━━━━━\n💡 **للحصول على إجابة أكيدة:**\n📞 اتصل بإدارة المدرسة\n📧 أرسل استفسار رسمي عبر البوت",
                parse_mode='Markdown'
            )
            return
            
        # بناء سياق الأدلة مع تحديد النوع (أدمن أو طلاب)
        evidence_context = ""
        for i, ev in enumerate(evidence_list):
            # نعطي Gemini كل المعلومات (بما في ذلك النوع)
            doc_type = ev.get('type', 'unknown')  # admin or student
            evidence_context += f"--- دليل {i+1} (النوع: {doc_type}, الرابط: {ev['link']}) ---\n{ev['text']}\n\n"

        # --- البرومبت الودود والذكي (محدّث) ---
        enhanced_prompt = f"""
أنت "مرشد الدراسة"، مساعد ذكي، ودود، ومتخصص في مساعدة طلاب معهد البعوث. مهمتك هي الدردشة مع الطالب والإجابة على سؤاله.

**سؤال الطالب:**
{user_question}

**الأدلة التي تم العثور عليها (المصدر الوحيد):**
{evidence_context}

**تعليمات الشخصية والرد (مهم جداً):**
1.  **كن ودوداً:** ابدأ الرد بترحيب أو تعليق لطيف. لا تكن "روبوتاً".
2.  **حلل الأدلة:** لديك أدلة من نوع "admin" (موثوقة ورسمية) وأدلة من نوع "student" (نقاشات قد تكون مفيدة).
3.  **أعط الأولوية للأدمن:** إذا وجدت إجابة واضحة في دليل "admin"، أجب بها بثقة.
4.  **استخدم نقاشات الطلاب:** إذا لم تجد إجابة "admin"، انظر إلى نقاشات "student". إذا كانت النقاشات مفيدة، يمكنك القول مثلاً: "لم أجد منشوراً رسمياً، ولكن يبدو من نقاشات الطلاب أن..."
5.  **كن صادقاً (ولكن ودوداً):** إذا كانت *كل* الأدلة (الأدمن والطلاب) لا تجيب على السؤال، لا تقل "لم أجد إجابة". قل شيئاً مثل: "أهلاً بك! بحثت لك في سجلات القناة، لكن لم أجد معلومة واضحة بخصوص هذا الموضوع. ربما يمكنك توجيه السؤال مباشرة في القناة للاحتياط."
6.  **لا تدردش خارج الموضوع:** ابقَ مركزاً على مساعدة الطالب في دراسته بالمعهد.

**الإجابة (بشكل ودود وتحليلي):**
"""
        # --- نهاية البرومبت ---
        
        response = chat_model.generate_content(enhanced_prompt)
        final_answer = response.text
        
        # 📌 بناء تذييل الأدلة يدوياً في Python
        evidence_footer = "\n\n━━━━━━━━━━━━━━━━\n📚 **المصادر من القناة:**\n"
        
        if evidence_list:
            # استخراج الروابط الفريدة
            links = [ev['link'] for ev in evidence_list]
            unique_links = list(dict.fromkeys(links))  # إزالة التكرار
            
            for i, link in enumerate(unique_links, 1):
                evidence_footer += f"{i}. {link}\n"
        else:
            evidence_footer = "\n\n(لم يتم العثور على أدلة محددة)"
        
        # إرسال الرد النهائي (الإجابة + التذييل)
        await update.message.reply_text(
            final_answer + evidence_footer,
            disable_web_page_preview=True,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"حدث خطأ أثناء معالجة الرد الذكي: {e}")
        await update.message.reply_text("عذراً، حدث خطأ تقني أثناء البحث عن إجابتك.")

def get_main_keyboard():
    """الحصول على لوحة المفاتيح الرئيسية"""
    keyboard = [
        [KeyboardButton("❓ طرح استفسار ذكي")], 
        [KeyboardButton("📊 آخر 5 أخبار رسمية")],
        [KeyboardButton("📰 الأخبار"), KeyboardButton("📚 حالة الكتب")],
        [KeyboardButton("📖 المكتبة"), KeyboardButton("📚 كتبي")],
        [KeyboardButton("⭐ المفضلة"), KeyboardButton("🔔 إشعارات")],
        [KeyboardButton("❓ مساعدة")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ============== أوامر أساسية ==============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البدء"""
    user = update.effective_user
    
    # التحقق إذا كان مستخدم جديد
    from database import is_new_user, mark_user_joined, get_active_ad
    is_first_time = is_new_user(user.id)
    
    add_user(user.id, user.full_name)
    
    # حذف رسالة الأمر السابقة
    try:
        await update.message.delete()
    except:
        pass
    
    # إذا كان مستخدم جديد، عرض الإعلان إن وُجد
    if is_first_time:
        active_ad = get_active_ad()
        if active_ad:
            ad_id, ad_title, ad_message, ad_image_file_id, ad_created = active_ad
            
            # عرض الإعلان مع الصورة إن وُجدت
            ad_text = (
                f"📢 **إعلان مدعوم** 📢\n\n"
                f"📌 **{escape_markdown(ad_title)}**\n\n"
                f"{escape_markdown(ad_message)}\n\n"
                f"━━━━━━━━━━━━━━━━━━━"
            )
            
            try:
                if ad_image_file_id:
                    # إرسال الإعلان مع الصورة
                    await context.bot.send_photo(
                        chat_id=user.id,
                        photo=ad_image_file_id,
                        caption=ad_text,
                        parse_mode='Markdown'
                    )
                else:
                    # إرسال الإعلان بدون صورة
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=ad_text,
                        parse_mode='Markdown'
                    )
                logger.info(f"عرض إعلان #{ad_id} للمستخدم الجديد {user.id}")
            except Exception as e:
                logger.error(f"خطأ في إرسال الإعلان: {e}")
        
        # تسجيل المستخدم كمستخدم قديم (لن يظهر له الإعلان مرة أخرى)
        mark_user_joined(user.id)
    
    # إرسال رسالة ترحيب جديدة
    sent_msg = await context.bot.send_message(
        chat_id=user.id,
        text=(
            f"🌟 **مرحباً بك {user.first_name}!** 🌟\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📚 **بوت مدرسة الأزهر الإعدادية (بنين)**\n"
            "الصف الثاني الإعدادي\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "✨ **يسعدنا خدمتك في:**\n\n"
            "📢 • متابعة آخر الأخبار والتحديثات\n"
            "📚 • معرفة حالة الكتب الدراسية\n"
            "📖 • تصفح المكتبة الرقمية\n"
            "🤝 • مشاركة كتبك ومقالاتك\n"
            "💡 • الإجابة على استفساراتك\n\n"
            "👇 **اختر ما تحتاجه من القائمة:**"
        ),
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    # حفظ معرف الرسالة الحالية
    context.user_data['last_bot_message'] = sent_msg.message_id
    logger.info(f"مستخدم: {user.id} - {user.full_name}")

# ============== معالج أزرار الكيبورد ==============

async def keyboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أزرار الكيبورد"""
    text = update.message.text
    user = update.effective_user
    
    # حذف رسالة المستخدم
    try:
        await update.message.delete()
    except:
        pass
    
    # ==================== الأخبار ====================
    if text == "📰 الأخبار":
        news_items = get_active_news(5)
        
        if news_items:
            news_text = (
                "╔═══════════════════════╗\n"
                "║   📰 **الأخبار الجديدة**   ║\n"
                "╚═══════════════════════╝\n\n"
            )
            
            for idx, news in enumerate(news_items, 1):
                title = escape_markdown(news[1])
                content = escape_markdown(news[2])
                date = news[3][:10]  # التاريخ فقط
                
                news_text += f"🔹 **{title}**\n"
                news_text += f"{content}\n"
                news_text += f"🕒 {date}\n\n"
        else:
            news_text = (
                "📰 **الأخبار**\n\n"
                "ℹ️ لا توجد أخبار جديدة حالياً.\n"
                "تابع البوت للحصول على آخر التحديثات!"
            )
        
        await update.message.reply_text(text=news_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        return
    
    # ==================== حالة الكتب ====================
    elif text == "📚 حالة الكتب":
        # عرض محسّن: ملخص حسب الحالة + آخر التحديثات + تصفح حسب الصف
        summary = get_books_inventory_summary()
        if summary and summary.get('total', 0) > 0:
            available = summary.get('available', 0)
            partial = summary.get('partial', 0)
            unavailable = summary.get('unavailable', 0)
            total = summary.get('total', 0)
            updates = get_recent_books_updates(3)
            
            status_text = (
                "╔══════════════════════╗\n"
                "║  📚 **حالة الكتب الدراسية**  ║\n"
                "╚══════════════════════╝\n\n"
                f"✅ متوفر: {available} | 🟨 جزئي: {partial} | ❌ غير متوفر: {unavailable}\n"
                f"إجمالي المواد: {total}\n\n"
            )
            if updates:
                status_text += "🆕 **آخر التحديثات:**\n"
                for (gr, subj, st, eta, upd_at) in updates:
                    eta_txt = f" • ⏳ {eta}" if eta else ""
                    st_emoji = '✅' if st == 'available' else ('🟨' if st == 'partial' else '❌')
                    status_text += f"{st_emoji} {gr} - {subj}{eta_txt}\n"
            
            # أزرار الصفوف + تحديثات + تنبيه
            grades = get_grades()
            from database import get_user_notifications_enabled
            notif_on = get_user_notifications_enabled(user.id)
            keyboard = []
            if grades:
                # خزن قائمة الصفوف في جلسة المستخدم لتقصير callback_data
                context.user_data['books_grades'] = grades
                row = []
                for i, g in enumerate(grades):
                    row.append(InlineKeyboardButton(g, callback_data=f'books_grade_idx_{i}'))
                    if (i + 1) % 2 == 0:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🆕 آخر التحديثات", callback_data='books_updates')])
            keyboard.append([InlineKeyboardButton(("🔔 إيقاف التنبيه" if notif_on else "🔔 تفعيل التنبيه"), callback_data='books_toggle_notif')])
            await update.message.reply_text(text=status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            # fallback للرسالة العامة القديمة
            status = get_books_status()
            if status:
                safe_message = escape_markdown(status['message'])
                safe_updated = escape_markdown(status['updated_at'])
                status_text = (
                    "╔══════════════════════╗\n"
                    "║  📚 **حالة الكتب الدراسية**  ║\n"
                    "╚══════════════════════╝\n\n"
                    f"📋 **الحالة الحالية:**\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"{safe_message}\n\n"
                    f"⏰ آخر تحديث: {safe_updated}"
                )
            else:
                status_text = "📚 **حالة الكتب**\n\n⚠️ لم يتم تحديث حالة الكتب بعد."
            await update.message.reply_text(text=status_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        return
    
    # ==================== المكتبة ====================
    elif text == "📖 المكتبة":
        stats = get_library_stats()
        keyboard = [
            [
                InlineKeyboardButton("🔍 بحث متقدم", callback_data='search_by_title'),
                InlineKeyboardButton("📤 رفع محتوى", callback_data='library_upload')
            ],
            [
                InlineKeyboardButton("📚 تصفح بالفئة", callback_data='browse_categories'),
                InlineKeyboardButton("📚 جميع المحتوى", callback_data='library_browse')
            ],
            [
                InlineKeyboardButton("🔥 الأكثر شعبية", callback_data='popular_books'),
                InlineKeyboardButton("⭐ الأعلى تقييماً", callback_data='top_rated_books')
            ],
            [
                InlineKeyboardButton("📝 المقالات", callback_data='view_articles'),
                InlineKeyboardButton("📣 المنشورات", callback_data='view_posts')
            ],
        ]
        library_text = (
            "╬═════════════════════════╗\n"
            "║     📖 **المكتبة الرقمية**     ║\n"
            "╚═════════════════════════╝\n\n"
            f"📊 **الإحصائيات:**\n"
            f"─────────────────────\n"
            f"📚 الكتب: **{stats['books']}** | 🖼️ الصور: **{stats['images']}**\n"
            f"📝 المقالات: **{stats['articles']}** | 📣 المنشورات: **{stats['posts']}**\n"
            f"📂 إجمالي: **{stats['total']}** عنصر\n"
            f"⌛ بانتظار الموافقة: **{stats['pending']}**\n\n"
            f"✨ **اختر ما تريد:**"
        )
        await update.message.reply_text(
            text=library_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    # ==================== كتبي ====================
    elif text == "📚 كتبي":
        user_books = get_user_library_items(user.id)
        
        if user_books:
            approved_count = sum(1 for book in user_books if book[3] == 1)
            pending_count = sum(1 for book in user_books if book[3] == 0)
            
            text_content = (
                f"📚 **كتبي**\n\n"
                f"📊 **إحصائياتك:**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✅ معتمدة: **{approved_count}** كتاب\n"
                f"⏳ بانتظار الموافقة: **{pending_count}** كتاب\n"
                f"📥 إجمالي التحميلات: **{sum(book[5] for book in user_books)}**\n\n"
                f"📚 **كتبك:**\n"
            )
            
            keyboard = []
            for idx, book in enumerate(user_books[:10], 1):
                book_id = book[0]
                title = book[1]
                safe_title = escape_markdown(title)
                approved = book[3]
                status_emoji = "✅" if approved == 1 else "⏳"
                
                text_content += f"{idx}. {status_emoji} **{safe_title}**\n"
                keyboard.append([InlineKeyboardButton(
                    f"{status_emoji} {title[:25]}...",
                    callback_data=f'my_book_{book_id}'
                )])
            
            await update.message.reply_text(
                text=text_content,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "📚 **كتبي**\n\n"
                "📦 لم ترفع أي كتب بعد.\n\n"
                "💡 اضغط على '📖 المكتبة' ثم '📤 رفع كتاب' لرفع كتابك الأول!",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
        return
    
    # ==================== مساعدة ====================
    elif text == "❓ مساعدة":
        help_text = (
            "╔════════════════════════╗\n"
            "║      💡 **المساعدة**      ║\n"
            "╚════════════════════════╝\n\n"
            "📋 **كيفية الاستخدام:**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔹 **الأخبار** - متابعة آخر أخبار المدرسة\n\n"
            "🔹 **حالة الكتب** - معرفة إذا نزلت الكتب\n\n"
            "🔹 **المكتبة** - تصفح ورفع الكتب والمقالات\n\n"
            "🔹 **كتبي** - إدارة كتبك الشخصية\n\n"
            "🔹 **استفسار** - إرسال أسئلتك للإدارة\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📧 للتواصل: zetsuserv@gmail.com"
        )
        await update.message.reply_text(text=help_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        return
    
    # ==================== المفضلة ====================
    elif text == "⭐ المفضلة":
        favorites = get_user_favorites(user.id)
        
        if favorites:
            text_content = (
                f"⭐ **كتبي المفضلة**\n\n"
                f"📚 لديك **{len(favorites)}** كتاب في المفضلة\n\n"
            )
            
            keyboard = []
            for idx, fav in enumerate(favorites[:10], 1):
                book_id = fav[0]
                title = fav[1]
                safe_title = escape_markdown(title)
                category = fav[2]
                safe_category = escape_markdown(category)
                downloads = fav[3]
                
                emoji = get_category_emoji(category)
                text_content += f"{idx}. {emoji} **{safe_title}**\n   📂 {safe_category} | 📅 {downloads} تحميل\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"{emoji} {title[:30]}...",
                    callback_data=f'view_book_{book_id}'
                )])
            
            await update.message.reply_text(
                text=text_content,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "⭐ **المفضلة**\n\n"
                "📦 لم تضف أي كتب للمفضلة بعد.\n\n"
                "💡 اضغط على ⭐ في تفاصيل أي كتاب لإضافته للمفضلة!",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
        return
    
    # ==================== الإشعارات ====================
    elif text == "🔔 إشعارات":
        notifications = get_user_notifications(user.id, unread_only=False)
        unread_count = get_unread_count(user.id)
        
        notification_text = format_notification_text(notifications)
        
        if unread_count > 0:
            notification_text = f"🔔 لديك **{unread_count}** إشعار جديد!\n\n" + notification_text
        
        keyboard = []
        if unread_count > 0:
            keyboard.append([InlineKeyboardButton("✅ وضع علامة مقروء على الكل", callback_data='mark_all_read')])
        
        await update.message.reply_text(
            text=notification_text,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else get_main_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # ==================== استفسار ذكي (RAG) ====================
    elif text == "❓ طرح استفسار ذكي":
        await update.message.reply_text(
            "╚═════════════════════════╝\n"
            "║   ❓ **طرح استفسار ذكي**   ║\n"
            "╚═════════════════════════╝\n\n"
            "تفضل، اكتب سؤالك وسأبحث لك عن إجابة من القناة الرسمية…\n\n"
            "💡 **مثال:**\n"
            "• متى الامتحانات؟\n"
            "• أين موقع المكتبة؟\n"
            "• ما شروط القبول؟",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        user_state[user.id] = "WAITING_FOR_QUERY"
        return
    
    # ==================== آخر 5 أخبار رسمية ====================
    elif text == "📊 آخر 5 أخبار رسمية":
        await handle_latest_news(update, context)
        return
    
    # ==================== استفسار عادي (للإدارة) ====================
    elif text == "💬 استفسار":
        await update.message.reply_text(
            "╔═════════════════════════╗\n"
            "║   💬 **إرسال استفسار**   ║\n"
            "╚═════════════════════════╝\n\n"
            "اكتب استفسارك وسيصل للإدارة مباشرة\n\n"
            "💡 **مثال:**\n"
            "• متى موعد امتحان الرياضيات؟\n"
            "• أين أجد كتاب العلوم؟",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        context.user_data['awaiting_query'] = True
        return

# ============== معالج الأزرار التفاعلية (Inline) ==============

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار التفاعلية Inline"""
    query = update.callback_query
    await query.answer()
    
    # ==================== معالجة الأزرار ====================
    if query.data == 'library_search':
        status = get_books_status()
        if status:
            safe_message = escape_markdown(status['message'])
            safe_updated = escape_markdown(status['updated_at'])
            status_text = (
                "╔══════════════════════╗\n"
                "║  📚 **حالة الكتب الدراسية**  ║\n"
                "╚══════════════════════╝\n\n"
                f"📋 **الحالة الحالية:**\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{safe_message}\n\n"
                f"⏰ آخر تحديث: {safe_updated}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 للرجوع: /start"
            )
        else:
            status_text = (
                "📚 **حالة الكتب الدراسية**\n\n"
                "⚠️ لم يتم تحديث حالة الكتب بعد.\n"
                "يرجى المتابعة لاحقاً.\n\n"
                "📌 للرجوع: /start"
            )
        await query.edit_message_text(text=status_text, parse_mode='Markdown')
    
    # ==================== المكتبة ====================
    elif query.data == 'library':
        stats = get_library_stats()
        keyboard = [
            [
                InlineKeyboardButton("🔍 بحث", callback_data='library_search'),
                InlineKeyboardButton("📤 رفع كتاب", callback_data='library_upload')
            ],
            [InlineKeyboardButton("📚 تصفح جميع الكتب", callback_data='library_browse')],
            [InlineKeyboardButton("🔙 الرجوع للقائمة", callback_data='back_to_main')],
        ]
        library_text = (
            "╔═════════════════════════╗\n"
            "║     📖 **المكتبة الرقمية**     ║\n"
            "╚═════════════════════════╝\n\n"
            f"📊 **الإحصائيات:**\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📚 الكتب المتاحة: **{stats['total']}** كتاب\n"
            f"⏳ بانتظار الموافقة: **{stats['pending']}**\n\n"
            f"✨ **اختر ما تريد:**"
        )
        await query.edit_message_text(
            text=library_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== البحث في المكتبة ====================
    elif query.data == 'library_search':
        await query.edit_message_text(
            "🔍 **البحث في المكتبة**\n\n"
            "اكتب اسم الكتاب أو الموضوع الذي تبحث عنه:\n\n"
            "مثال: رياضيات، علوم، تاريخ\n\n"
            "📌 للرجوع: /start",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_library_search'] = True
    
    # ==================== رفع محتوى - اختيار النوع ====================
    elif query.data == 'library_upload':
        user_name = escape_markdown(query.from_user.first_name)
        keyboard = [
            [InlineKeyboardButton("📚 كتاب", callback_data='upload_book')],
            [InlineKeyboardButton("🖼️ صورة", callback_data='upload_image')],
            [InlineKeyboardButton("📝 مقال", callback_data='upload_article')],
            [InlineKeyboardButton("📣 منشور", callback_data='upload_post')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='library')],
        ]
        upload_text = (
            f"╬═══════════════════════════╗\n"
            f"║   📤 **رفع محتوى جديد**   ║\n"
            f"╚═══════════════════════════╝\n\n"
            f"👋 مرحباً عزيزي التلميذ **{user_name}**\n\n"
            f"─────────────────────\n\n"
            f"🌟 **ماذا تريد أن ترفع؟**\n\n"
            f"📚 **كتاب:** ملفات PDF أو مستندات علمية (ملف)\n"
            f"🖼️ **صورة:** صور توضيحية أو تعليمية (ملف)\n"
            f"📝 **مقال:** مقالة نصية مفصلة (نص مكتوب - 100 حرف+)\n"
            f"📣 **منشور:** منشور نصي قصير (نص مكتوب - 30 حرف+)\n\n"
            f"─────────────────────\n\n"
            f"💡 **ملاحظة:**\n"
            f"• 📚🖼️ = تحتاج ملف | 📝📣 = كتابة نص\n"
            f"• جميع المحتويات تخضع لمراجعة الإدارة\n\n"
            f"👇 **اختر نوع المحتوى:**"
        )
        await query.edit_message_text(
            text=upload_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== معالجات رفع المحتوى ====================
    elif query.data.startswith('upload_'):
        content_type = query.data.split('_')[1]
        context.user_data['content_type'] = content_type
        
        if content_type == 'post':
            # للمنشورات - نص قصير
            await query.edit_message_text(
                "📣 **نشر منشور جديد**\n\n"
                "📝 اكتب محتوى المنشور (على الأقل 30 حرف):   "
                "\n\n💡 **مثال:**\n"
                "\"هل تعلم أن الرياضيات هي أساس كل العلوم؟ تعلمها بجد لتصبح ناجحاً!\""
                "\n\n⚠️ **شروط:**\n"
                "• حد أدنى: 30 حرف\n"
                "• يجب أن يكون مفيد وهادف\n\n"
                "📌 للرجوع: /start",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_post_content'] = True
        elif content_type == 'article':
            # للمقالات - نص طويل
            await query.edit_message_text(
                "📝 **كتابة مقال جديد**\n\n"
                "✍️ اكتب محتوى المقال (على الأقل 100 حرف):   "
                "\n\n💡 **مثال:**\n"
                "\"الرياضيات هي لغة العلوم وأساس التقدم التكنولوجي. "
                "من خلال دراسة الأرقام والمعادلات، نستطيع فهم الكون...\""
                "\n\n⚠️ **شروط:**\n"
                "• حد أدنى: 100 حرف (مقال مفصل)\n"
                "• يجب أن يكون علمي ومفيد\n"
                "• نص منظم ومنسق\n\n"
                "📌 للرجوع: /start",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_article_content'] = True
        else:
            # للكتب والصور فقط - يحتاج ملف
            content_names = {
                'book': 'كتاب',
                'image': 'صورة'
            }
            content_icons = {
                'book': '📚',
                'image': '🖼️'
            }
            await query.edit_message_text(
                f"{content_icons[content_type]} **رفع {content_names[content_type]}**\n\n"
                f"📎 أرسل الملف الآن (PDF/صورة/مستند)\n\n"
                f"📌 للرجوع: /start",
                parse_mode='Markdown'
            )
            context.user_data['awaiting_library_file'] = True
    
    # ==================== عرض المقالات ====================
    elif query.data == 'view_articles':
        conn = sqlite3.connect('school_bot.db')
        c = conn.cursor()
        c.execute('''SELECT id, title, description, uploader_name, upload_date, views
                     FROM library 
                     WHERE approved = 1 AND content_type = 'article'
                     ORDER BY upload_date DESC 
                     LIMIT 10''')
        articles = c.fetchall()
        conn.close()
        
        if articles:
            text = "📝 **المقالات الأخيرة**\n\n"
            keyboard = []
            
            for idx, article in enumerate(articles, 1):
                article_id = article[0]
                title = escape_markdown(article[1])
                author = escape_markdown(article[3])
                date = article[4][:10]
                views = article[5]
                
                text += f"{idx}. 📝 **{title[:40]}\\.\\.\\.**\n"
                text += f"   👤 {author} | 📅 {date} | 👁️ {views}\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"📝 {title[:35]}...",
                    callback_data=f'view_article_{article_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='library')])
        else:
            text = "📝 **المقالات**\n\n⚠️ لا توجد مقالات حالياً."
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='library')]]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== عرض مقال ====================
    elif query.data.startswith('view_article_'):
        article_id = int(query.data.split('_')[2])
        conn = sqlite3.connect('school_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM library WHERE id = ?", (article_id,))
        article = c.fetchone()
        conn.close()
        
        if not article:
            await query.edit_message_text("❌ لم يتم العثور على المقال.")
            return
        
        # زيادة عداد المشاهدات
        increment_views(article_id)
        
        title = html.escape(article[1])
        content = html.escape(article[2])
        author = html.escape(article[7])
        date = article[8][:10]
        views = article[12] + 1
        
        # تنسيق مميز للمقال باستخدام HTML (blockquote بدون مائل)
        article_text = (
            f"<b>📝 {title}</b>\n\n"
            f"<blockquote>{content}</blockquote>\n\n"
            f"<i>✍️ بقلم: {author} • 📅 {date} • 👁️ {views} مشاهدة</i>"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='view_articles')]]
        
        await query.edit_message_text(
            text=article_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    # ==================== عرض المنشورات ====================
    elif query.data == 'view_posts':
        conn = sqlite3.connect('school_bot.db')
        c = conn.cursor()
        c.execute('''SELECT id, title, description, uploader_name, upload_date, views
                     FROM library 
                     WHERE approved = 1 AND content_type = 'post'
                     ORDER BY upload_date DESC 
                     LIMIT 10''')
        posts = c.fetchall()
        conn.close()
        
        if posts:
            text = "📣 **المنشورات الأخيرة**\n\n"
            keyboard = []
            
            for idx, post in enumerate(posts, 1):
                post_id = post[0]
                title = post[1]
                author = post[3]
                date = post[4][:10]
                views = post[5]
                
                text += f"{idx}. 📣 **{title[:40]}...**\n"
                text += f"   👤 {author} | 📅 {date} | 👁️ {views}\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"📣 {title[:35]}...",
                    callback_data=f'view_post_{post_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='library')])
        else:
            text = "📣 **المنشورات**\n\n⚠️ لا توجد منشورات حالياً."
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='library')]]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== عرض منشور ====================
    elif query.data.startswith('view_post_'):
        post_id = int(query.data.split('_')[2])
        conn = sqlite3.connect('school_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM library WHERE id = ?", (post_id,))
        post = c.fetchone()
        conn.close()
        
        if not post:
            await query.edit_message_text("❌ لم يتم العثور على المنشور.")
            return
        
        # زيادة عداد المشاهدات
        increment_views(post_id)
        
        title = post[1]
        content = post[2]
        author = post[7]
        date = post[8][:10]
        views = post[12] + 1
        
        # تنسيق مميز للمنشور باستخدام HTML
        post_text = (
            f"┌───────────────────────┐\n"
            f"│   📣 <b>منشور</b>   │\n"
            f"└───────────────────────┘\n\n"
            f"<b>📝 {title}</b>\n\n"
            f"<blockquote>{content}</blockquote>\n\n"
            f"───────────────────\n"
            f"👤 <b>بقلم:</b> {author}\n"
            f"📅 <b>التاريخ:</b> {date}\n"
            f"👁️ <b>المشاهدات:</b> {views}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='view_posts')]]
        
        await query.edit_message_text(
            text=post_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    
    # ==================== تصفح المكتبة ====================
    elif query.data == 'library_browse':
        # عرض أحدث كتاب فقط بشكل مبسط
        await render_latest_item(query, content_filter='book')

    elif query.data == 'library_latest_select':
        # اختيار النوع
        keyboard = [[
            InlineKeyboardButton("📖 كتاب", callback_data='library_latest_book'),
            InlineKeyboardButton("🖼️ صورة", callback_data='library_latest_image')
        ], [
            InlineKeyboardButton("📝 مقال", callback_data='library_latest_article'),
            InlineKeyboardButton("📣 منشور", callback_data='library_latest_post')
        ], [InlineKeyboardButton("🔄 الأحدث - الكل", callback_data='library_latest_all')],
           [InlineKeyboardButton("🔙 رجوع", callback_data='library')]]
        await query.edit_message_text(
            text="اختر نوع المحتوى لإظهار أحدث عنصر:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith('library_latest_'):
        flt = query.data.split('_', 2)[2]
        await render_latest_item(query, flt)
    
    # ==================== حالة الكتب المتقدمة ====================
    elif query.data.startswith('books_grade_idx_'):
        try:
            idx = int(query.data.split('books_grade_idx_', 1)[1])
        except Exception:
            await query.answer("⚠️ خطأ بالزر")
            return
        grades_list = context.user_data.get('books_grades', [])
        if idx < 0 or idx >= len(grades_list):
            await query.answer("⚠️ انتهت صلاحية الزر")
            return
        grade = grades_list[idx]
        from database import get_books_by_grade
        items = get_books_by_grade(grade)
        
        def st_emoji(s):
            return '✅' if s == 'available' else ('🟨' if s == 'partial' else '❌')
        
        if items:
            text = f"📚 **{grade}**\n\n"
            for subj, st, eta, note, upd in items:
                eta_txt = f" ⏳ {eta}" if eta else ""
                note_txt = f" — {escape_markdown(note)}" if note else ""
                text += f"{st_emoji(st)} {escape_markdown(subj)}{eta_txt}{note_txt}\n"
        else:
            text = f"📚 **{grade}**\n\nلا توجد بيانات بعد."
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel_btn' if is_admin(query.from_user.id) else 'back_to_main')]]),
            parse_mode='Markdown'
        )
    
    elif query.data == 'books_updates':
        from database import get_recent_books_updates
        updates = get_recent_books_updates(10)
        if updates:
            text = "🆕 **آخر التحديثات على حالة الكتب**\n\n"
            for gr, subj, st, eta, upd in updates:
                st_e = '✅' if st == 'available' else ('🟨' if st == 'partial' else '❌')
                eta_txt = f" • ⏳ {eta}" if eta else ""
                text += f"{st_e} {gr} - {subj}{eta_txt} • {upd}\n"
        else:
            text = "لا توجد تحديثات بعد."
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]]), parse_mode='Markdown')
    
    elif query.data == 'books_toggle_notif':
        from database import get_user_notifications_enabled, set_user_notifications_enabled
        on = get_user_notifications_enabled(query.from_user.id)
        set_user_notifications_enabled(query.from_user.id, not on)
        await query.answer("✅ تم تحديث إعداد الإشعارات")
        # إعادة عرض لوحة حالة الكتب المبسطة
        summary = get_books_inventory_summary()
        if summary and summary.get('total', 0) > 0:
            available = summary.get('available', 0)
            partial = summary.get('partial', 0)
            unavailable = summary.get('unavailable', 0)
            total = summary.get('total', 0)
            updates = get_recent_books_updates(3)
            status_text = (
                "╔══════════════════════╗\n"
                "║  📚 **حالة الكتب الدراسية**  ║\n"
                "╚══════════════════════╝\n\n"
                f"✅ متوفر: {available} | 🟨 جزئي: {partial} | ❌ غير متوفر: {unavailable}\n"
                f"إجمالي المواد: {total}\n\n"
            )
            if updates:
                status_text += "🆕 **آخر التحديثات:**\n"
                for (gr, subj, st, eta, upd_at) in updates:
                    eta_txt = f" • ⏳ {eta}" if eta else ""
                    st_emoji = '✅' if st == 'available' else ('🟨' if st == 'partial' else '❌')
                    status_text += f"{st_emoji} {gr} - {subj}{eta_txt}\n"
            grades = get_grades()
            notif_on = get_user_notifications_enabled(query.from_user.id)
            keyboard = []
            if grades:
                row = []
                for idx, g in enumerate(grades, 1):
                    row.append(InlineKeyboardButton(g, callback_data=f'books_grade_{g}'))
                    if idx % 2 == 0:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
            keyboard.append([InlineKeyboardButton("🆕 آخر التحديثات", callback_data='books_updates')])
            keyboard.append([InlineKeyboardButton(("🔔 إيقاف التنبيه" if notif_on else "🔔 تفعيل التنبيه"), callback_data='books_toggle_notif')])
            await query.edit_message_text(text=status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await query.edit_message_text(text="📚 **حالة الكتب**\n\nلم يتم إدخال بيانات بعد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]]), parse_mode='Markdown')
    
    # ==================== المساعدة ====================
    elif query.data == 'help':
        help_text = (
            "╔════════════════════════╗\n"
            "║      💡 **المساعدة**      ║\n"
            "╚════════════════════════╝\n\n"
            "📋 **كيفية الاستخدام:**\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔹 **/start** - العودة للقائمة الرئيسية\n\n"
            "🔹 **الأخبار** - متابعة آخر أخبار المدرسة\n\n"
            "🔹 **حالة الكتب** - معرفة إذا نزلت الكتب\n\n"
            "🔹 **المكتبة** - تصفح ورفع الكتب والمقالات\n\n"
            "🔹 **استفسار** - إرسال أسئلتك للإدارة\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📧 للتواصل: zetsuserv@gmail.com\n\n"
            "📌 للرجوع: /start"
        )
        await query.edit_message_text(text=help_text, parse_mode='Markdown')
    
    # ==================== كتبي ====================
    elif query.data == 'my_books':
        user_books = get_user_library_items(query.from_user.id)
        
        if user_books:
            approved_count = sum(1 for book in user_books if book[3] == 1)
            pending_count = sum(1 for book in user_books if book[3] == 0)
            
            text = (
                f"📚 **كتبي**\n\n"
                f"📊 **إحصائياتك:**\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✅ معتمدة: **{approved_count}** كتاب\n"
                f"⏳ بانتظار الموافقة: **{pending_count}** كتاب\n"
                f"📥 إجمالي التحميلات: **{sum(book[5] for book in user_books)}**\n\n"
                f"📚 **كتبك:**\n"
            )
            
            keyboard = []
            for idx, book in enumerate(user_books[:10], 1):
                book_id = book[0]
                title = book[1]
                approved = book[3]
                status_emoji = "✅" if approved == 1 else "⏳"
                
                text += f"{idx}. {status_emoji} **{title}**\n"
                keyboard.append([InlineKeyboardButton(
                    f"{status_emoji} {title[:25]}...",
                    callback_data=f'my_book_{book_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data='back_to_main')])
            
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            text = (
                "📚 **كتبي**\n\n"
                "📦 لم ترفع أي كتب بعد.\n\n"
                "💡 اضغط على '📖 المكتبة' ثم '📤 رفع كتاب/مقال' لرفع كتابك الأول!"
            )
            keyboard = [[InlineKeyboardButton("🔙 الرجوع", callback_data='back_to_main')]]
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    # ==================== تفاصيل كتاب شخصي ====================
    elif query.data.startswith('my_book_'):
        book_id = int(query.data.split('_')[2])
        item = get_library_item(book_id)
        
        if not item or item[6] != query.from_user.id:
            await query.edit_message_text("❌ لم يتم العثور على الكتاب.")
            return
        
        title = item[1]
        description = item[2] or "لا يوجد وصف"
        approved = item[9]
        upload_date = item[8]
        downloads = item[11]
        
        status = "✅ معتمد" if approved == 1 else "⏳ بانتظار الموافقة"
        
        text = (
            f"📖 **تفاصيل كتابك**\n\n"
            f"📚 **العنوان:** {title}\n\n"
            f"📝 **الوصف:** {description}\n\n"
            f"🏷️ **الحالة:** {status}\n"
            f"📅 **تاريخ الرفع:** {upload_date}\n"
            f"📥 **عدد التحميلات:** {downloads}\n\n"
        )
        
        keyboard = []
        if approved == 1:
            text += "✅ كتابك متاح في المكتبة لجميع الطلاب!"
        else:
            text += "⏳ كتابك بانتظار مراجعة الإدارة."
        
        keyboard.append([InlineKeyboardButton("🗑️ حذف الكتاب", callback_data=f'delete_my_book_{book_id}')])
        keyboard.append([InlineKeyboardButton("🔙 الرجوع لكتبي", callback_data='my_books')])
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== حذف كتاب شخصي ====================
    elif query.data.startswith('delete_my_book_'):
        book_id = int(query.data.split('_')[3])
        item = get_library_item(book_id)
        
        if not item or item[6] != query.from_user.id:
            await query.answer("❌ ليس لديك صلاحية لحذف هذا الكتاب", show_alert=True)
            return
        
        title = item[1]
        delete_library_item(book_id)
        
        await query.edit_message_text(
            f"✅ **تم حذف الكتاب**\n\n"
            f"📚 العنوان: {title}\n\n"
            f"تم حذف الكتاب بنجاح.",
            parse_mode='Markdown'
        )
        logger.info(f"حذف كتاب {book_id} بواسطة المالك {query.from_user.id}")
    
    # ==================== الاستفسار ====================
    elif query.data == 'query':
        await query.edit_message_text(
            "╔═════════════════════════╗\n"
            "║   💬 **إرسال استفسار**   ║\n"
            "╚═════════════════════════╝\n\n"
            "اكتب استفسارك وسيصل لإدارة الفصل\n\n"
            "💡 **مثال:**\n"
            "• متى موعد امتحان الرياضيات؟\n"
            "•متى نحصل على الكتب؟\n\n"
            "📌 للرجوع: /start",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_query'] = True
    
    # ==================== الرجوع للقائمة ====================
    elif query.data == 'back_to_main':
        keyboard = [
            [InlineKeyboardButton("📰 الأخبار", callback_data='news')],
            [InlineKeyboardButton("📖 المكتبة", callback_data='library')],
            [InlineKeyboardButton("📚 كتبي", callback_data='my_books'), InlineKeyboardButton("⭐ المفضلة", callback_data='favorites')],
            [InlineKeyboardButton("📊 إحصائياتي", callback_data='my_stats')],
            [InlineKeyboardButton("❓ مساعدة", callback_data='help'), InlineKeyboardButton("💬 استفسار", callback_data='query')],
        ]
        await query.edit_message_text(
            text="🏠 **القائمة الرئيسية**\n\nاختر ما تحتاجه:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== الإحصائيات الشخصية ====================
    elif query.data == 'my_stats':
        user_books = get_user_library_items(query.from_user.id)
        favorites = get_user_favorites(query.from_user.id)
        
        # حساب الإحصائيات
        approved_count = sum(1 for book in user_books if book[3] == 1)
        pending_count = sum(1 for book in user_books if book[3] == 0)
        total_downloads = sum(book[5] for book in user_books) if user_books else 0
        
        stats_text = (
            f"📊 **إحصائياتك الشخصية**\n\n"
            f"🎓 **المساهمات:**\n"
            f"───────────────\n"
            f"✅ معتمدة: **{approved_count}**\n"
            f"⏳ بانتظار الموافقة: **{pending_count}**\n"
            f"📂 إجمالي: **{len(user_books)}**\n\n"
            f"📈 **التفاعل:**\n"
            f"───────────────\n"
            f"📅 إجمالي التحميلات لمحتواك: **{total_downloads}**\n"
            f"⭐ عدد المفضلات: **{len(favorites)}**\n\n"
            f"🌟 **استمر في المساهمة والنشر!**"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]]
        await query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== المفضلة ====================
    elif query.data == 'favorites':
        favorites = get_user_favorites(query.from_user.id)
        
        if favorites:
            text_content = (
                f"⭐ **كتبي المفضلة**\n\n"
                f"📚 لديك **{len(favorites)}** عنصر في المفضلة\n\n"
            )
            
            keyboard = []
            for idx, fav in enumerate(favorites[:10], 1):
                book_id = fav[0]
                title = fav[1]
                category = fav[2]
                downloads = fav[3]
                
                text_content += f"{idx}. 📖 **{title[:40]}**\n   📂 {category} | 📅 {downloads} تحميل\n\n"
                
                keyboard.append([InlineKeyboardButton(
                    f"📖 {title[:30]}...",
                    callback_data=f'view_book_{book_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')])
            
            await query.edit_message_text(
                text=text_content,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "⭐ **المفضلة**\n\n"
                "📦 لم تضف أي عناصر للمفضلة بعد.\n\n"
                "💡 اضغط على ⭐ في تفاصيل أي محتوى لإضافته!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]]),
                parse_mode='Markdown'
            )
    
    # ==================== عرض الأخبار ====================
    elif query.data == 'news':
        news_items = get_active_news(5)
        
        if news_items:
            news_text = (
                "╬═══════════════════════╗\n"
                "║   📰 **الأخبار الجديدة**   ║\n"
                "╚═══════════════════════╝\n\n"
            )
            
            for idx, news in enumerate(news_items, 1):
                title = news[1]
                content = news[2]
                date = news[3][:10]
                
                news_text += f"🔹 **{title}**\n"
                news_text += f"{content}\n"
                news_text += f"🕒 {date}\n\n"
        else:
            news_text = (
                "📰 **الأخبار**\n\n"
                "ℹ️ لا توجد أخبار جديدة حالياً.\n"
                "تابع البوت للحصول على آخر التحديثات!"
            )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')]]
        await query.edit_message_text(
            text=news_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ==================== أزرار لوحة الأدمن ====================
    elif query.data == 'admin_books_status':
        if not is_admin(query.from_user.id):
            await query.edit_message_text("⚠️ ليس لديك صلاحية.")
            return
        # اختيار الصف ثم المادة ثم الحالة
        default_grades = ["الأول الإعدادي", "الثاني الإعدادي", "الثالث الإعدادي"]
        grades = get_grades()
        grades = grades if grades else default_grades
        # خزن الصفوف في جلسة الأدمن
        context.user_data['admin_bs_grades'] = grades
        rows = []
        row = []
        for i, g in enumerate(grades):
            row.append(InlineKeyboardButton(g, callback_data=f'admin_bs_grade_idx_{i}'))
            if (i + 1) % 2 == 0:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel_btn')])
        await query.edit_message_text(
            "📚 **تحديث حالة الكتب**\n\nاختر الصف:",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('admin_bs_grade_idx_'):
        try:
            gidx = int(query.data.split('admin_bs_grade_idx_', 1)[1])
        except Exception:
            await query.answer("⚠️ خطأ بالزر")
            return
        grades = context.user_data.get('admin_bs_grades', [])
        if gidx < 0 or gidx >= len(grades):
            await query.answer("⚠️ انتهت صلاحية الزر")
            return
        grade = grades[gidx]
        # إحضار مواد الصف أو عرض قائمة افتراضية
        from database import get_subjects_by_grade
        subjects = get_subjects_by_grade(grade)
        if not subjects:
            subjects = ["رياضيات", "علوم", "لغة عربية", "لغة إنجليزية", "دين", "دراسات"]
        # خزّن المواد لهذا الصف بمفتاح الفهرس
        if 'admin_bs_subjects' not in context.user_data:
            context.user_data['admin_bs_subjects'] = {}
        context.user_data['admin_bs_subjects'][gidx] = subjects
        rows = []
        row = []
        for sidx, s in enumerate(subjects):
            row.append(InlineKeyboardButton(s, callback_data=f'admin_bs_subject_idx_{gidx}_{sidx}'))
            if (sidx + 1) % 2 == 0:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("➕ إضافة مادة", callback_data=f'admin_bs_subject_add_idx_{gidx}')])
        rows.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_books_status')])
        await query.edit_message_text(
            f"📚 **{grade}**\n\nاختر المادة:",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('admin_bs_subject_add_idx_'):
        try:
            gidx = int(query.data.split('admin_bs_subject_add_idx_', 1)[1])
        except Exception:
            await query.answer("⚠️ خطأ بالزر")
            return
        # اطلب اسم المادة
        context.user_data['awaiting_new_subject_gidx'] = gidx
        await query.edit_message_text(
            "✏️ أرسل اسم المادة الجديدة:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=f'admin_bs_grade_idx_{gidx}')]])
        )
    
    elif query.data.startswith('admin_bs_subject_idx_'):
        try:
            parts = query.data.split('_')  # ['admin','bs','subject','idx',gidx,sidx]
            gidx = int(parts[-2])
            sidx = int(parts[-1])
        except Exception:
            await query.answer("⚠️ خطأ بالزر")
            return
        grades = context.user_data.get('admin_bs_grades', [])
        subjects_map = context.user_data.get('admin_bs_subjects', {})
        subjects = subjects_map.get(gidx, [])
        if gidx >= len(grades) or sidx >= len(subjects):
            await query.answer("⚠️ انتهت صلاحية الزر")
            return
        grade = grades[gidx]
        subject = subjects[sidx]
        # اختيار الحالة (قصيرة)
        rows = [[
            InlineKeyboardButton("✅ متوفر", callback_data=f'admin_bs_status_idx_{gidx}_{sidx}_a'),
            InlineKeyboardButton("🟨 جزئي", callback_data=f'admin_bs_status_idx_{gidx}_{sidx}_p'),
            InlineKeyboardButton("❌ غير متوفر", callback_data=f'admin_bs_status_idx_{gidx}_{sidx}_u'),
        ], [InlineKeyboardButton("🔙 رجوع", callback_data=f'admin_bs_grade_idx_{gidx}')]]
        await query.edit_message_text(
            f"📘 {grade} - {subject}\n\nاختر الحالة:",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('admin_bs_status_new_idx_'):
        try:
            parts = query.data.split('_')  # ['admin','bs','status','new','idx',gidx,code]
            gidx = int(parts[-2])
            code = parts[-1]
        except Exception:
            await query.answer("⚠️ خطأ بالزر")
            return
        grades = context.user_data.get('admin_bs_grades', [])
        pending = context.user_data.get('pending_subjects', {})
        if gidx >= len(grades) or gidx not in pending:
            await query.answer("⚠️ انتهت صلاحية الزر")
            return
        grade = grades[gidx]
        subject = pending[gidx]
        status_val = {'a': 'available', 'p': 'partial', 'u': 'unavailable'}.get(code, 'available')
        from database import upsert_book_inventory, get_all_users_notifications_enabled
        upsert_book_inventory(grade, subject, status_val, eta=None, note=None, admin_id=query.from_user.id)
        # ضمّ المادة الجديدة في الخريطة حتى تُعرض لاحقاً في الجلسة
        if 'admin_bs_subjects' not in context.user_data:
            context.user_data['admin_bs_subjects'] = {}
        g_subjects = context.user_data['admin_bs_subjects'].get(gidx, [])
        if subject not in g_subjects:
            g_subjects.append(subject)
        context.user_data['admin_bs_subjects'][gidx] = g_subjects
        # إشعار
        users_on = get_all_users_notifications_enabled()
        st_txt = 'متوفر' if status_val == 'available' else ('جزئي' if status_val == 'partial' else 'غير متوفر')
        notif_msg = f"📚 إضافة مادة وتحديث حالتها\n\n{grade} - {subject}: {st_txt}"
        for uid in users_on[:500]:
            try:
                await context.bot.send_message(chat_id=uid, text=notif_msg)
            except Exception:
                pass
        await query.edit_message_text(
            f"✅ تمت إضافة المادة وتحديد حالتها: {grade} - {subject} ({st_txt})",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_books_status')]])
        )

    elif query.data.startswith('admin_bs_status_idx_'):
        try:
            parts = query.data.split('_')  # ['admin','bs','status','idx',gidx,sidx,code]
            gidx = int(parts[-3])
            sidx = int(parts[-2])
            code = parts[-1]
        except Exception:
            await query.answer("⚠️ خطأ بالزر")
            return
        grades = context.user_data.get('admin_bs_grades', [])
        subjects_map = context.user_data.get('admin_bs_subjects', {})
        subjects = subjects_map.get(gidx, [])
        if gidx >= len(grades) or sidx >= len(subjects):
            await query.answer("⚠️ انتهت صلاحية الزر")
            return
        grade = grades[gidx]
        subject = subjects[sidx]
        status_val = {'a': 'available', 'p': 'partial', 'u': 'unavailable'}.get(code, 'available')
        # تحديث
        from database import upsert_book_inventory, get_all_users_notifications_enabled
        upsert_book_inventory(grade, subject, status_val, eta=None, note=None, admin_id=query.from_user.id)
        # إشعار للمستخدمين المفعّل لديهم التنبيه
        users_on = get_all_users_notifications_enabled()
        st_txt = 'متوفر' if status_val == 'available' else ('جزئي' if status_val == 'partial' else 'غير متوفر')
        notif_msg = f"📚 تحديث حالة الكتب\n\n{grade} - {subject}: {st_txt}"
        for uid in users_on[:500]:  # حماية من الإرسال الضخم
            try:
                await context.bot.send_message(chat_id=uid, text=notif_msg)
            except Exception:
                pass
        await query.edit_message_text(
            f"✅ تم تحديث حالة: {grade} - {subject} ({st_txt})",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='admin_books_status')]])
        )
    
    elif query.data == 'admin_library':
        if not is_admin(query.from_user.id):
            await query.edit_message_text("⚠️ ليس لديك صلاحية.")
            return
        
        keyboard = [
            [InlineKeyboardButton("📤 رفع كتاب للمكتبة", callback_data='admin_upload_book')],
            [InlineKeyboardButton("✅ الموافقة على الكتب", callback_data='admin_approve_books')],
            [InlineKeyboardButton("🗑️ حذف كتاب", callback_data='admin_delete_book')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel_btn')],
        ]
        await query.edit_message_text(
            "📖 **إدارة المكتبة**\n\nاختر العملية:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'admin_upload_book':
        if not is_admin(query.from_user.id):
            return
        await query.edit_message_text(
            "📤 **رفع كتاب للمكتبة**\n\n"
            "أرسل الملف (PDF/صورة) الآن",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_admin_upload'] = True
    
    elif query.data == 'admin_approve_books':
        if not is_admin(query.from_user.id):
            return
        
        pending = get_pending_library_items()
        if pending:
            # عرض أول كتاب مع أزرار الموافقة/الرفض
            item = pending[0]
            book_id = item[0]
            title = item[1]
            uploader = item[2]
            date = item[3]
            
            text = (
                f"📖 **كتاب بانتظار الموافقة**\n\n"
                f"🆔 الرقم: `{book_id}`\n"
                f"📚 العنوان: **{title}**\n"
                f"👤 بواسطة: {uploader}\n"
                f"📅 التاريخ: {date}\n\n"
                f"📊 عدد الكتب المنتظرة: {len(pending)}"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ موافق", callback_data=f'approve_{book_id}'),
                    InlineKeyboardButton("❌ رفض", callback_data=f'reject_{book_id}')
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data='admin_library')]
            ]
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            text = "✅ لا توجد كتب بانتظار الموافقة"
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_library')]]
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    elif query.data == 'admin_panel_btn':
        if not is_admin(query.from_user.id):
            return
        
        # الحصول على الإحصائيات
        stats = get_admin_stats()
        
        admin_text = (
            "🔧 **لوحة تحكم الأدمن**\n\n"
            "📊 **إحصائيات عامة:**\n"
            "──────────────\n"
            f"👥 المستخدمون: **{stats['total_users']}**\n"
            f"📚 الكتب المعتمدة: **{stats['approved_books']}**\n"
            f"⌛ بانتظار الموافقة: **{stats['pending_books']}**\n"
            f"📅 إجمالي التحميلات: **{stats['total_downloads']}**\n"
            f"⭐ عدد التقييمات: **{stats['total_ratings']}**\n\n"
            "🚀 **اختر العملية:**"
        )
        
        keyboard = [
            [InlineKeyboardButton("📰 إدارة الأخبار", callback_data='admin_news')],
            [InlineKeyboardButton("➕ إضافة خبر جديد", callback_data='add_news')],
            [InlineKeyboardButton("📢 إرسال إعلان جماعي", callback_data='send_news')],
            [InlineKeyboardButton("🎬 إدارة الإعلانات", callback_data='admin_ads')],
            [InlineKeyboardButton("📚 تحديث حالة الكتب", callback_data='admin_books_status')],
            [InlineKeyboardButton("📖 إدارة المكتبة", callback_data='admin_library')],
            [InlineKeyboardButton("📊 إحصائيات تفصيلية", callback_data='detailed_stats')],
        ]
        await query.edit_message_text(
            admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'send_news':
        if not is_admin(query.from_user.id):
            return
        await query.edit_message_text(
            "📢 **إرسال إعلان جماعي**\n\n"
            "اكتب الرسالة التي تريد إرسالها لجميع الطلاب:",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_broadcast'] = True
    
    elif query.data == 'list_users':
        if not is_admin(query.from_user.id):
            return
        users = get_all_users()
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel_btn')]]
        await query.edit_message_text(
            f"👥 **إحصائيات المستخدمين**\n\n"
            f"📊 العدد الإجمالي: **{len(users)}** مستخدم",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ========== عرض تفاصيل كتاب ==========
    elif query.data.startswith('view_book_'):
        book_id = int(query.data.split('_')[2])
        # استخدام الدالة الجديدة لعرض التفاصيل مع المعرض
        from advanced_features import show_book_details_with_gallery
        await show_book_details_with_gallery(query, context, book_id)
    
    # ========== تحميل الكتاب ==========
    elif query.data.startswith('download_book_'):
        book_id = int(query.data.split('_')[2])
        item = get_library_item(book_id)
        
        if not item:
            await query.answer("❌ لم يتم العثور على الكتاب", show_alert=True)
            return
        
        title = item[1]
        file_id = item[3]
        file_type = item[4]
        content_type = item[5] if len(item) > 5 else 'book'
        
        # التحقق من أن العنصر ليس منشوراً أو مقالاً (لا يوجد ملف)
        if content_type in ['post', 'article']:
            await query.answer("⚠️ هذا المحتوى لا يحتوي على ملف للتحميل!", show_alert=True)
            return
        
        # زيادة عداد التحميلات
        increment_downloads(book_id)
        
        # إرسال الملف
        await query.answer("📥 جاري إرسال الكتاب...")
        
        try:
            # محاولة الإرسال من file_id أولاً (إذا كان موجوداً)
            if file_id and file_id != '':
                # إرسال حسب نوع الملف المحفوظ
                if file_type == 'photo':
                    await context.bot.send_photo(
                        chat_id=query.from_user.id,
                        photo=file_id,
                        caption=f"📚 **{title}**\n\n✅ تم التحميل بنجاح!",
                        parse_mode='Markdown'
                    )
                else:
                    await context.bot.send_document(
                        chat_id=query.from_user.id,
                        document=file_id,
                        caption=f"📚 **{title}**\n\n✅ تم التحميل بنجاح!",
                        parse_mode='Markdown'
                    )
            else:
                # إذا لم يكن هناك file_id، جرب الملفات من library_files
                from database import get_library_files
                import os
                
                files = get_library_files(book_id)
                
                if not files:
                    await query.answer("❌ لم يتم العثور على ملفات لهذا الكتاب", show_alert=True)
                    return
                
                # إرسال أول ملف متاح
                for f_id, f_type, caption, local_path in files:
                    if f_id:
                        # إرسال من file_id
                        await context.bot.send_document(
                            chat_id=query.from_user.id,
                            document=f_id,
                            caption=f"📚 **{title}**\n\n✅ تم التحميل بنجاح!",
                            parse_mode='Markdown'
                        )
                        break
                    elif local_path:
                        # إرسال من الملف المحلي
                        file_path = local_path.replace('\\', '/')
                        if not os.path.isabs(file_path):
                            file_path = os.path.join(os.getcwd(), file_path)
                        
                        if os.path.exists(file_path):
                            with open(file_path, 'rb') as f:
                                await context.bot.send_document(
                                    chat_id=query.from_user.id,
                                    document=f,
                                    caption=f"📚 **{title}**\n\n✅ تم التحميل بنجاح!",
                                    parse_mode='Markdown',
                                    filename=os.path.basename(file_path)
                                )
                            break
                        else:
                            logger.error(f"الملف المحلي غير موجود: {file_path}")
                else:
                    # لم يتم إرسال أي ملف
                    await query.answer("❌ لم يتم العثور على ملفات متاحة", show_alert=True)
                    return
            
            await query.message.reply_text(
                f"✅ تم إرسال الكتاب إليك!\n\n"
                f"📚 {title}\n\n"
                f"📌 للرجوع للمكتبة: /start",
                parse_mode='Markdown'
            )
            
            logger.info(f"تحميل كتاب {book_id} بواسطة {query.from_user.id}")
        except Exception as e:
            await query.message.reply_text(
                f"❌ حدث خطأ أثناء إرسال الملف.\n"
                f"يرجى المحاولة لاحقاً."
            )
            logger.error(f"خطأ في تحميل كتاب {book_id}: {e}")
    
    # ========== معاينة المحتوى للأدمن ==========
    elif query.data.startswith('preview_admin_'):
        if not is_admin(query.from_user.id):
            await query.answer("⚠️ ليس لديك صلاحية", show_alert=True)
            return
        
        item_id = int(query.data.split('_')[2])
        item = get_library_item(item_id)
        
        if not item:
            await query.edit_message_text("❌ لم يتم العثور على المحتوى.")
            return
        
        title = item[1]
        description = item[2] or "لا يوجد وصف"
        uploader_name = item[7]
        content_type = item[5] if len(item) > 5 else 'book'
        file_id = item[3]
        file_type = item[4]
        
        # إعداد نص المعاينة
        preview_text = (
            f"👁️ **معاينة المحتوى**\n\n"
            f"🆔 **رقم المحتوى:** `{item_id}`\n"
            f"📖 **العنوان:** {title}\n"
            f"📝 **الوصف/المحتوى:** {description[:500]}...\n" if len(description) > 500 else f"📝 **الوصف/المحتوى:** {description}\n"
        )
        preview_text += (
            f"👤 **المرسل:** {uploader_name}\n"
            f"📊 **النوع:** {content_type}\n\n"
        )
        
        # التحقق من وجود ملفات متعددة
        from database import get_library_files
        files = get_library_files(item_id)
        if files:
            preview_text += f"📁 **عدد الملفات:** {len(files)}\n\n"
        
        # أزرار الموافقة والرفض
        keyboard = [
            [
                InlineKeyboardButton("✅ موافق", callback_data=f'approve_{item_id}'),
                InlineKeyboardButton("❌ رفض", callback_data=f'reject_{item_id}')
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_approve_books')]
        ]
        
        await query.edit_message_text(
            text=preview_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # إرسال الملف إذا كان موجوداً (ليس منشور أو مقال)
        if file_id and file_id != 'text_content' and content_type not in ['post', 'article']:
            try:
                if file_type == 'photo':
                    await context.bot.send_photo(
                        chat_id=query.from_user.id,
                        photo=file_id,
                        caption=f"📎 معاينة الملف المرفق للمحتوى #{item_id}"
                    )
                else:
                    await context.bot.send_document(
                        chat_id=query.from_user.id,
                        document=file_id,
                        caption=f"📎 معاينة الملف المرفق للمحتوى #{item_id}"
                    )
            except Exception as e:
                logger.error(f"خطأ في إرسال معاينة الملف: {e}")
    
    # ========== معالجة الموافقة/الرفض من الأزرار ==========
    elif query.data.startswith('approve_'):
        if not is_admin(query.from_user.id):
            return
        
        book_id = int(query.data.split('_')[1])
        item = get_library_item(book_id)
        
        if not item:
            await query.edit_message_text("❌ لم يتم العثور على الكتاب.")
            return
        
        # الموافقة
        approve_library_item(book_id, query.from_user.id)
        title = item[1]
        uploader_name = item[7]
        uploader_id = item[6]
        
        # إرسال إشعار للمستخدم
        await send_notification_to_user(
            context, uploader_id,
            "تمت الموافقة على كتابك",
            f"مبروك! تمت الموافقة على كتاب '{title}' وهو الآن متاح لجميع الطلاب!",
            'book_approved'
        )
        
        await query.edit_message_text(
            f"✅ **تمت الموافقة بنجاح!**\n\n"
            f"📚 العنوان: {title}\n"
            f"👤 بواسطة: {uploader_name}\n\n"
            f"الكتاب الآن متاح في المكتبة!"
        )
        logger.info(f"الموافقة على كتاب {book_id}")
        
        # التحقق من وجود كتب أخرى
        pending = get_pending_library_items()
        if pending:
            await query.message.reply_text(
                f"📚 يوجد **{len(pending)}** كتب أخرى بانتظار الموافقة.\n"
                f"استخدم /admin_panel لمراجعتها.",
                parse_mode='Markdown'
            )
    
    elif query.data.startswith('reject_'):
        if not is_admin(query.from_user.id):
            return
        
        book_id = int(query.data.split('_')[1])
        item = get_library_item(book_id)
        
        if not item:
            await query.edit_message_text("❌ لم يتم العثور على الكتاب.")
            return
        
        title = item[1]
        uploader_id = item[6]
        delete_library_item(book_id)
        
        # إرسال إشعار للمستخدم
        await send_notification_to_user(
            context, uploader_id,
            "تم رفض كتابك",
            f"للأسف، تم رفض كتاب '{title}'. يرجى مراجعة قواعد النشر.",
            'book_rejected'
        )
        
        await query.edit_message_text(
            f"❌ **تم رفض الكتاب**\n\n"
            f"📚 العنوان: {title}\n\n"
            f"تم حذف الكتاب من قاعدة البيانات."
        )
        logger.info(f"رفض كتاب {book_id}")
        
        # التحقق من وجود كتب أخرى
        pending = get_pending_library_items()
        if pending:
            await query.message.reply_text(
                f"📚 يوجد **{len(pending)}** كتب أخرى بانتظار الموافقة.\n"
                f"استخدم /admin_panel لمراجعتها.",
                parse_mode='Markdown'
            )
    
    # ========== تقييم الكتب ==========
    elif query.data.startswith('rate_book_'):
        book_id = int(query.data.split('_')[2])
        text = "⭐ **قيّم الكتاب**\n\nاختر عدد النجوم:"
        await query.edit_message_text(
            text=text,
            reply_markup=get_rating_keyboard(book_id),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('rate_'):
        # استخراج book_id و rating
        parts = query.data.split('_')
        if len(parts) == 3:
            book_id = int(parts[1])
            rating = int(parts[2])
            
            # حفظ التقييم
            success = add_rating(book_id, query.from_user.id, rating)
            
            if success:
                item = get_library_item(book_id)
                uploader_id = item[6]
                title = item[1]
                
                # إشعار صاحب الكتاب
                await send_notification_to_user(
                    context, uploader_id,
                    "تقييم جديد لكتابك",
                    f"حصل كتابك '{title}' على تقييم {rating}/5 ⭐",
                    'new_rating'
                )
                
                await query.answer("✅ شكراً على تقييمك!", show_alert=True)
                # إعادة عرض تفاصيل الكتاب
                from advanced_features import show_book_details_with_gallery
                await show_book_details_with_gallery(query, context, book_id)
            else:
                await query.answer("❌ لقد قيّمت هذا الكتاب مسبقاً", show_alert=True)
    
    # ========== المفضلة ==========
    elif query.data.startswith('fav_'):
        book_id = int(query.data.split('_')[1])
        success = add_to_favorites(query.from_user.id, book_id)
        
        if success:
            await query.answer("✅ تمت إضافة الكتاب للمفضلة!", show_alert=True)
        else:
            await query.answer("❌ الكتاب موجود بالفعل", show_alert=True)
        
        # إعادة عرض تفاصيل الكتاب
        from advanced_features import show_book_details_with_gallery
        await show_book_details_with_gallery(query, context, book_id)
    
    elif query.data.startswith('unfav_'):
        book_id = int(query.data.split('_')[1])
        remove_from_favorites(query.from_user.id, book_id)
        await query.answer("✅ تمت إزالة الكتاب من المفضلة", show_alert=True)
        
        # إعادة عرض تفاصيل الكتاب
        from advanced_features import show_book_details_with_gallery
        await show_book_details_with_gallery(query, context, book_id)
    
    # ========== الفئات والبحث المتقدم ==========
    elif query.data == 'browse_categories':
        await query.edit_message_text(
            "📚 **تصفح حسب الفئة**\n\nاختر فئة:",
            reply_markup=get_categories_keyboard(),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('category_'):
        category = query.data.split('_', 1)[1]
        books = get_library_by_category(category)
        
        text = f"{get_category_emoji(category)} **{category}**\n\n"
        text += format_book_list(books)
        
        keyboard = []
        for book in books[:10]:
            keyboard.append([InlineKeyboardButton(
                f"📖 {book[1][:35]}...",
                callback_data=f'view_book_{book[0]}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data='browse_categories')])
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'popular_books':
        books = get_popular_books(10)
        text = "🔥 **الكتب الأكثر شعبية**\n\n"
        text += format_book_list(books)
        
        keyboard = []
        for book in books[:10]:
            keyboard.append([InlineKeyboardButton(
                f"📖 {book[1][:35]}...",
                callback_data=f'view_book_{book[0]}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data='library')])
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'top_rated_books':
        books = get_top_rated_books(10)
        text = "⭐ **الكتب الأعلى تقييماً**\n\n"
        
        for idx, book in enumerate(books[:10], 1):
            book_id = book[0]
            title = book[1]
            category = book[2]
            total_rating = book[3]
            rating_count = book[4]
            avg = total_rating / rating_count if rating_count > 0 else 0
            
            text += f"{idx}. **{title}**\n"
            text += f"   {get_category_emoji(category)} {category} | {format_rating_stars(avg)} ({avg:.1f}/5)\n\n"
        
        keyboard = []
        for book in books[:10]:
            keyboard.append([InlineKeyboardButton(
                f"📖 {book[1][:35]}...",
                callback_data=f'view_book_{book[0]}'
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data='library')])
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'search_by_title':
        await query.edit_message_text(
            "🔍 **البحث عن كتاب**\n\n"
            "اكتب اسم الكتاب أو الموضوع:\n\n"
            "💡 مثال: رياضيات، علوم، ملخص",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_library_search'] = True
    
    # ========== إشعارات ==========
    elif query.data == 'mark_all_read':
        notifications = get_user_notifications(query.from_user.id, unread_only=True)
        for notif in notifications:
            mark_notification_read(notif[0])
        
        await query.answer("✅ تم وضع علامة مقروء على جميع الإشعارات", show_alert=True)
        
        # تحديث العرض
        notifications = get_user_notifications(query.from_user.id, unread_only=False)
        notification_text = format_notification_text(notifications)
        
        await query.edit_message_text(
            text=notification_text,
            parse_mode='Markdown'
        )
    
    # ========== إدارة الأخبار (أدمن) ==========
    elif query.data == 'admin_news':
        if not is_admin(query.from_user.id):
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة خبر جديد", callback_data='add_news')],
            [InlineKeyboardButton("📋 عرض الأخبار", callback_data='view_all_news')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel_btn')]
        ]
        
        await query.edit_message_text(
            "📰 **إدارة الأخبار**\n\nاختر العملية:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'add_news':
        if not is_admin(query.from_user.id):
            return
        
        await query.edit_message_text(
            "📰 **إضافة خبر جديد**\n\n"
            "اكتب عنوان الخبر:\n\n"
            "💡 مثال: امتحان الرياضيات - غداً",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_news_title'] = True
    
    elif query.data == 'view_all_news':
        if not is_admin(query.from_user.id):
            return
        
        news_items = get_active_news(10)
        
        if news_items:
            text = "📰 **جميع الأخبار**\n\n"
            keyboard = []
            
            for idx, news in enumerate(news_items, 1):
                news_id = news[0]
                title = news[1]
                date = news[3][:10]
                
                text += f"{idx}. **{title}**\n   🕒 {date}\n\n"
                keyboard.append([InlineKeyboardButton(
                    f"❌ حذف: {title[:20]}...",
                    callback_data=f'delete_news_{news_id}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_news')])
        else:
            text = "📰 **الأخبار**\n\nℹ️ لا توجد أخبار."
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_news')]]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('delete_news_'):
        if not is_admin(query.from_user.id):
            return
        
        news_id = int(query.data.split('_')[2])
        delete_news(news_id)
        
        await query.answer("✅ تم حذف الخبر", show_alert=True)
        
        # إعادة عرض قائمة الأخبار
        news_items = get_active_news(10)
        
        if news_items:
            text = "📰 **جميع الأخبار**\n\n"
            keyboard = []
            
            for idx, news in enumerate(news_items, 1):
                nid = news[0]
                title = news[1]
                date = news[3][:10]
                
                text += f"{idx}. **{title}**\n   🕒 {date}\n\n"
                keyboard.append([InlineKeyboardButton(
                    f"❌ حذف: {title[:20]}...",
                    callback_data=f'delete_news_{nid}'
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_news')])
        else:
            text = "📰 **الأخبار**\n\nℹ️ لا توجد أخبار."
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_news')]]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ========== إدارة الإعلانات (أدمن) ==========
    elif query.data == 'admin_ads':
        if not is_admin(query.from_user.id):
            return
        
        from database import get_all_ads
        ads = get_all_ads()
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة إعلان جديد", callback_data='add_new_ad')],
            [InlineKeyboardButton("📋 عرض جميع الإعلانات", callback_data='view_all_ads')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel_btn')]
        ]
        
        text = (
            f"🎬 **إدارة الإعلانات**\n\n"
            f"📊 **عدد الإعلانات:** {len(ads)}\n\n"
            f"👇 **اختر عملية:**"
        )
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == 'add_new_ad':
        if not is_admin(query.from_user.id):
            return
        
        await query.edit_message_text(
            "🎬 **إضافة إعلان جديد**\n\n"
            "📝 اكتب عنوان الإعلان:\n\n"
            "💡 **مثال:** خصم 50% على المنتجات",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_ad_title'] = True
    
    elif query.data == 'view_all_ads':
        if not is_admin(query.from_user.id):
            return
        
        from database import get_all_ads
        ads = get_all_ads()
        
        if ads:
            text = "🎬 **جميع الإعلانات**\n\n"
            keyboard = []
            
            for idx, ad in enumerate(ads, 1):
                ad_id, ad_title, ad_message, ad_image, is_active, created_at = ad
                status_emoji = "✅" if is_active else "❌"
                date = created_at[:10]
                
                text += f"{idx}. {status_emoji} **{ad_title[:30]}**\n   📅 {date}\n\n"
                
                # أزرار لكل إعلان
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_emoji} {ad_title[:25]}...",
                        callback_data=f'view_ad_{ad_id}'
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_ads')])
        else:
            text = "🎬 **الإعلانات**\n\nℹ️ لا توجد إعلانات."
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_ads')]]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('view_ad_'):
        if not is_admin(query.from_user.id):
            return
        
        ad_id = int(query.data.split('_')[2])
        from database import get_all_ads
        ads = get_all_ads()
        ad = next((a for a in ads if a[0] == ad_id), None)
        
        if not ad:
            await query.answer("⚠️ لم يتم العثور على الإعلان", show_alert=True)
            return
        
        ad_id, ad_title, ad_message, ad_image, is_active, created_at = ad
        status_text = "✅ نشط" if is_active else "❌ غير نشط"
        
        text = (
            f"🎬 **تفاصيل الإعلان**\n\n"
            f"🆔 **الرقم:** `{ad_id}`\n"
            f"📌 **العنوان:** {escape_markdown(ad_title)}\n"
            f"📝 **المحتوى:** {escape_markdown(ad_message[:200])}{'...' if len(ad_message) > 200 else ''}\n"
            f"🖼️ **صورة:** {'\u2705 نعم' if ad_image else '\u274c لا'}\n"
            f"🔄 **الحالة:** {status_text}\n"
            f"📅 **التاريخ:** {created_at[:16]}\n\n"
        )
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "❌ إيقاف" if is_active else "✅ تفعيل",
                    callback_data=f'toggle_ad_{ad_id}'
                ),
                InlineKeyboardButton("🗑️ حذف", callback_data=f'delete_ad_{ad_id}')
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data='view_all_ads')]
        ]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data.startswith('toggle_ad_'):
        if not is_admin(query.from_user.id):
            return
        
        ad_id = int(query.data.split('_')[2])
        from database import get_all_ads, toggle_ad_status
        ads = get_all_ads()
        ad = next((a for a in ads if a[0] == ad_id), None)
        
        if ad:
            current_status = ad[4]
            toggle_ad_status(ad_id, not current_status)
            await query.answer("✅ تم تحديث الحالة", show_alert=True)
            
            # إعادة عرض تفاصيل الإعلان
            ads = get_all_ads()
            ad = next((a for a in ads if a[0] == ad_id), None)
            ad_id, ad_title, ad_message, ad_image, is_active, created_at = ad
            status_text = "✅ نشط" if is_active else "❌ غير نشط"
            
            text = (
                f"🎬 **تفاصيل الإعلان**\n\n"
                f"🆔 **الرقم:** `{ad_id}`\n"
                f"📌 **العنوان:** {escape_markdown(ad_title)}\n"
                f"📝 **المحتوى:** {escape_markdown(ad_message[:200])}{'...' if len(ad_message) > 200 else ''}\n"
                f"🖼️ **صورة:** {'\u2705 نعم' if ad_image else '\u274c لا'}\n"
                f"🔄 **الحالة:** {status_text}\n"
                f"📅 **التاريخ:** {created_at[:16]}\n\n"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        "❌ إيقاف" if is_active else "✅ تفعيل",
                        callback_data=f'toggle_ad_{ad_id}'
                    ),
                    InlineKeyboardButton("🗑️ حذف", callback_data=f'delete_ad_{ad_id}')
                ],
                [InlineKeyboardButton("🔙 رجوع", callback_data='view_all_ads')]
            ]
            
            await query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    elif query.data.startswith('delete_ad_'):
        if not is_admin(query.from_user.id):
            return
        
        ad_id = int(query.data.split('_')[2])
        from database import delete_ad
        delete_ad(ad_id)
        
        await query.answer("✅ تم حذف الإعلان", show_alert=True)
        
        # إعادة عرض قائمة الإعلانات
        from database import get_all_ads
        ads = get_all_ads()
        
        if ads:
            text = "🎬 **جميع الإعلانات**\n\n"
            keyboard = []
            
            for idx, ad in enumerate(ads, 1):
                ad_id, ad_title, ad_message, ad_image, is_active, created_at = ad
                status_emoji = "✅" if is_active else "❌"
                date = created_at[:10]
                
                text += f"{idx}. {status_emoji} **{ad_title[:30]}**\n   📅 {date}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_emoji} {ad_title[:25]}...",
                        callback_data=f'view_ad_{ad_id}'
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_ads')])
        else:
            text = "🎬 **الإعلانات**\n\nℹ️ لا توجد إعلانات."
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_ads')]]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    # ========== رفع ملفات متعددة ==========
    elif query.data == 'finish_upload':
        if 'upload_files' not in context.user_data or not context.user_data['upload_files']:
            await query.answer("⚠️ لم يتم رفع أي ملفات", show_alert=True)
            return
        
        files_count = len(context.user_data['upload_files'])
        
        await query.edit_message_text(
            f"📝 **اكتب عنواناً للملفات:**\n\n"
            f"📊 عدد الملفات: **{files_count}**\n\n"
            f"💡 مثال: ملخص الرياضيات - الفصل الثالث",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_library_file'] = False
        context.user_data['awaiting_library_title'] = True
    
    elif query.data == 'cancel_upload':
        # حذف جميع الملفات المرفوعة
        context.user_data.pop('upload_files', None)
        context.user_data.pop('awaiting_library_file', None)
        
        await query.edit_message_text(
            "❌ **تم إلغاء عملية الرفع**\n\n"
            "📌 للرجوع: /start",
            parse_mode='Markdown'
        )
    
    # ========== معالجات المعرض والملفات المتعددة ==========
    elif query.data.startswith('show_gallery_'):
        book_id = int(query.data.split('_')[2])
        from advanced_features import show_gallery_handler
        await show_gallery_handler(query, context, book_id)
    
    elif query.data.startswith('download_all_'):
        book_id = int(query.data.split('_')[2])
        from advanced_features import download_all_files_handler
        await download_all_files_handler(query, context, book_id)
    
    # ========== إحصائيات تفصيلية ==========
    elif query.data == 'detailed_stats':
        if not is_admin(query.from_user.id):
            return
        
        stats = get_admin_stats()
        popular = get_popular_books(5)
        top_rated = get_top_rated_books(5)
        
        text = (
            "📊 **إحصائيات تفصيلية**\n\n"
            "📦 **ملخص عام:**\n"
            "──────────────\n"
            f"👥 إجمالي المستخدمين: **{stats['total_users']}**\n"
            f"📚 كتب معتمدة: **{stats['approved_books']}**\n"
            f"⌛ بانتظار الموافقة: **{stats['pending_books']}**\n"
            f"📅 إجمالي التحميلات: **{stats['total_downloads']}**\n"
            f"⭐ عدد التقييمات: **{stats['total_ratings']}**\n\n"
        )
        
        if popular:
            text += "🔥 **الأكثر شعبية:**\n"
            for idx, book in enumerate(popular[:3], 1):
                text += f"{idx}. {book[1][:30]} (📅 {book[3]})\n"
            text += "\n"
        
        if top_rated:
            text += "⭐ **الأعلى تقييماً:**\n"
            for idx, book in enumerate(top_rated[:3], 1):
                avg = book[3] / book[4] if book[4] > 0 else 0
                text += f"{idx}. {book[1][:30]} ({avg:.1f}⭐)\n"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel_btn')]]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# ============== أدوات عرض المكتبة (عرض عنصر واحد حديث + خيارات) ==============

def get_content_type_emoji(ct: str) -> str:
    return {
        'book': '📖',
        'image': '🖼️',
        'article': '📝',
        'post': '📣'
    }.get(ct, '📄')

async def render_latest_item(query, content_filter: str):
    from database import get_library_items_paginated

    flt = None if content_filter in ['all', 'any'] else content_filter
    items = get_library_items_paginated(flt if flt else None, page=1, page_size=1)

    names_singular = {
        'all': 'محتوى',
        'book': 'كتاب',
        'image': 'صورة',
        'article': 'مقال',
        'post': 'منشور'
    }
    label = names_singular.get(content_filter, 'محتوى')

    if not items:
        await query.edit_message_text(
            text=f"📚 لا يوجد أي {label} حديث متاح حالياً.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data='library')]])
        )
        return

    iid, ititle, uploader, downloads, ctype, category, up_at = items[0]
    icon = get_content_type_emoji(ctype)
    title_text = f"📚 أحدث {names_singular.get(ctype, 'محتوى')}"
    body = (
        f"{icon} **{ititle}**\n\n"
        f"📂 {category or 'عام'}\n"
        f"👤 {uploader}\n"
        f"📥 {downloads} تحميل\n"
    )
    text = f"{title_text}\n\n{body}"

    keyboard = [
        [InlineKeyboardButton("👁️ عرض التفاصيل", callback_data=f'view_book_{iid}')],
        [InlineKeyboardButton("🗂 تغيير النوع", callback_data='library_latest_select')],
        [InlineKeyboardButton("🔙 رجوع", callback_data='library')]
    ]

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# (احتفظنا بوظيفة الترقيم السابقة للاستخدام المستقبلي إن لزم)
# ============== أدوات عرض المكتبة (ترقيم صفحات + فلاتر) ==============

def get_content_type_emoji(ct: str) -> str:
    return {
        'book': '📖',
        'image': '🖼️',
        'article': '📝',
        'post': '📣'
    }.get(ct, '📄')

async def render_library_browse(query, content_filter: str, page: int, page_size: int = 8):
    from database import get_library_items_paginated, count_library_items

    # بيانات
    total = count_library_items(content_filter)
    items = get_library_items_paginated(content_filter, page, page_size)

    # رأس
    filter_names = {
        'all': 'الكل',
        'book': 'كتب',
        'image': 'صور',
        'article': 'مقالات',
        'post': 'منشورات'
    }
    title = f"📚 **جميع المحتويات** — {filter_names.get(content_filter, 'الكل')}"

    if not items:
        text = title + "\n\n⚠️ لا توجد عناصر للعرض."
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='library')]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return

    # نص القائمة
    lines = []
    for idx, (iid, ititle, uploader, downloads, ctype, category, up_at) in enumerate(items, 1 + (page - 1) * page_size):
        icon = get_content_type_emoji(ctype)
        ititle_cut = ititle[:40]
        lines.append(f"{idx}. {icon} **{ititle_cut}**\n   {category or 'عام'} • 👤 {uploader} • 📥 {downloads}")

    body = "\n\n".join(lines)
    text = f"{title}\n\n{body}\n\n📌 اختر عنصراً لعرض التفاصيل"

    # لوحة الفلاتر
    def filter_btn(flt):
        label = filter_names[flt]
        return InlineKeyboardButton(("✅ " if flt == content_filter else "") + label, callback_data=f'library_browse_{flt}_1')

    filters_row = [filter_btn(f) for f in ['all', 'book', 'image', 'article', 'post']]

    # أزرار العناصر
    item_buttons = [[InlineKeyboardButton(f"{get_content_type_emoji(ctype)} {ititle[:30]}...", callback_data=f'view_book_{iid}')]
                    for (iid, ititle, _, _, ctype, _, _) in items]

    # ترقيم الصفحات
    max_page = (total + page_size - 1) // page_size
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f'library_browse_{content_filter}_{page-1}'))
    nav_row.append(InlineKeyboardButton(f"صفحة {page}/{max_page}", callback_data='noop'))
    if page < max_page:
        nav_row.append(InlineKeyboardButton("التالي ➡️", callback_data=f'library_browse_{content_filter}_{page+1}'))

    # تجميع اللوحة
    keyboard = [filters_row] + item_buttons + [nav_row, [InlineKeyboardButton("🔙 رجوع", callback_data='library')]]

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ============== معالج الرسائل ==============

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية والملفات"""
    user = update.effective_user
    text = update.message.text if update.message.text else ""
    
    # ========== معالجة الاستفسار الذكي (RAG) ==========
    if user_state.get(user.id) == "WAITING_FOR_QUERY":
        await handle_smart_query(update, context)
        user_state[user.id] = None  # إنهاء حالة الاستفسار
        return
    
    # ========== تحديث حالة الكتب (أدمن) ==========
    if context.user_data.get('awaiting_books_status'):
        if not is_admin(user.id):
            await update.message.reply_text("⚠️ ليس لديك صلاحية.")
            return
        
        # حذف الرسالة من الأدمن
        try:
            await update.message.delete()
        except:
            pass
        
        set_books_status(text, user.id)
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "✅ تم تحديث حالة الكتب بنجاح!\n\n"
                "يمكن للطلاب الآن رؤية التحديث."
            )
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        context.user_data['awaiting_books_status'] = False
        logger.info(f"تحديث حالة الكتب بواسطة {user.id}")
        return
    
    # ========== إضافة إعلان (أدمن) ==========
    if context.user_data.get('awaiting_ad_title'):
        if not is_admin(user.id):
            return
        
        context.user_data['ad_title'] = text
        await update.message.reply_text(
            "🎬 **ممتاز!**\n\n"
            "📝 الآن اكتب محتوى الإعلان:\n\n"
            "💡 **مثال:** سجّل الآن واحصل على خصم حصري!",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_ad_title'] = False
        context.user_data['awaiting_ad_content'] = True
        return
    
    if context.user_data.get('awaiting_ad_content'):
        if not is_admin(user.id):
            return
        
        context.user_data['ad_content'] = text
        await update.message.reply_text(
            "🎬 **رائع!**\n\n"
            "🖼️ ارفق صورة للإعلان (اختياري)\n\n"
            "⚠️ **أو اكتب 'skip' للتخطي**",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_ad_content'] = False
        context.user_data['awaiting_ad_image'] = True
        return
    
    if context.user_data.get('awaiting_ad_image'):
        if not is_admin(user.id):
            return
        
        if text.strip().lower() in ['skip', 'تخطي', 'تخطى']:
            from database import add_ad
            ad_title = context.user_data.get('ad_title')
            ad_content = context.user_data.get('ad_content')
            
            ad_id = add_ad(ad_title, ad_content, None, user.id)
            safe_title = escape_markdown(ad_title)
            
            await update.message.reply_text(
                f"✅ **تم إضافة الإعلان بنجاح!**\n\n"
                f"🆔 **الرقم:** `{ad_id}`\n"
                f"📌 **العنوان:** {safe_title}\n\n"
                f"✅ الإعلان نشط وسيظهر لجميع المستخدمين الجدد\\.\n\n"
                f"🔧 استخدم /admin\\_panel لإدارة الإعلانات",
                parse_mode='Markdown'
            )
            
            context.user_data.pop('ad_title', None)
            context.user_data.pop('ad_content', None)
            context.user_data.pop('awaiting_ad_image', None)
            logger.info(f"إضافة إعلان {ad_id} بدون صورة بواسطة {user.id}")
            return
    
    # ========== إضافة خبر (أدمن) ==========
    if context.user_data.get('awaiting_news_title'):
        if not is_admin(user.id):
            return
        
        context.user_data['news_title'] = text
        await update.message.reply_text(
            "📰 الآن اكتب محتوى الخبر:",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_news_title'] = False
        context.user_data['awaiting_news_content'] = True
        return
    
    if context.user_data.get('awaiting_news_content'):
        if not is_admin(user.id):
            return
        
        title = context.user_data.get('news_title')
        content = text
        
        # حفظ الخبر
        news_id = add_news(title, content, user.id, priority=0)
        
        # حماية العنوان من أخطاء Markdown
        safe_title = escape_markdown(title)
        
        await update.message.reply_text(
            f"✅ **تم إضافة الخبر بنجاح!**\n\n"
            f"🆔 رقم الخبر: {news_id}\n"
            f"📰 العنوان: {safe_title}\n\n"
            f"يمكنك الآن إرسال إعلان لجميع المستخدمين لإخبارهم\\.\n\n"
            f"📢 استخدم /admin\\_panel لإرسال إعلان جماعي",
            parse_mode='Markdown'
        )
        
        context.user_data.pop('news_title', None)
        context.user_data.pop('awaiting_news_content', None)
        logger.info(f"إضافة خبر جديد {news_id} بواسطة {user.id}")
        return
    
    # ========== البحث في المكتبة ==========
    if context.user_data.get('awaiting_library_search'):
        # حذف رسالة البحث من المستخدم
        try:
            await update.message.delete()
        except:
            pass
        
        results = search_library(text)
        if results:
            safe_search_text = escape_markdown(text)
            response = f"🔍 **نتائج البحث عن:** {safe_search_text}\n\n"
            for item in results[:5]:
                safe_title = escape_markdown(item[1])
                safe_desc = escape_markdown(item[2]) if item[2] else ""
                safe_uploader = escape_markdown(item[4])
                response += f"📚 **{safe_title}**\n"
                if item[2]:
                    response += f"   📝 {safe_desc}\n"
                response += f"   👤 {safe_uploader} | 📥 {item[5]} تحميل\n"
                response += f"   للتحميل: /download\\_{item[0]}\n\n"
            response += "\n📌 للرجوع: /start"
        else:
            safe_search_text = escape_markdown(text)
            response = f"⚠️ لم يتم العثور على نتائج لـ: {safe_search_text}\n\n📌 للرجوع: /start"
        
        # حذف الرسالة السابقة وإرسال الجديدة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        sent_msg = await update.message.reply_text(response, parse_mode='Markdown')
        context.user_data['last_bot_message'] = sent_msg.message_id
        context.user_data['awaiting_library_search'] = False
        return
    
    # ========== استفسار ==========
    if context.user_data.get('awaiting_query'):
        # حذف رسالة الاستفسار من المستخدم
        try:
            await update.message.delete()
        except:
            pass
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        # إرسال الاستفسار عبر البريد الإلكتروني
        email_sent = send_inquiry_email(
            user_id=user.id,
            user_name=user.full_name,
            inquiry_text=text
        )
        
        email_status = "\n📧 تم إرسال استفسارك للإدارة عبر البريد الإلكتروني\\." if email_sent else ""
        
        # حماية نص الاستفسار من أخطاء Markdown
        safe_text = escape_markdown(text)
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ **تم استلام استفسارك**\n\n"
                f"📩 \"{safe_text}\"\n\n"
                f"سيتم الرد عليك في أقرب وقت\\.{email_status}\n\n"
                f"📌 للرجوع: /start"
            ),
            parse_mode='Markdown'
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        context.user_data['awaiting_query'] = False
        logger.info(f"استفسار من {user.id}: {text} | Email sent: {email_sent}")
        return
    
    # ========== معالجة استلام عنوان الكتاب ==========
    if context.user_data.get('awaiting_library_title'):
        # حذف رسالة العنوان
        try:
            await update.message.delete()
        except:
            pass
        
        title = text
        context.user_data['upload_title'] = title
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📝 اكتب وصفاً مختصراً للكتاب:\n\n"
                "مثال: ملخص شامل للفصل الثالث مع أمثلة"
            )
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        context.user_data['awaiting_library_title'] = False
        context.user_data['awaiting_library_desc'] = True
        return
    
    # ========== معالجة استلام محتوى المنشور ==========
    if context.user_data.get('awaiting_post_content'):
        # حذف رسالة المستخدم
        try:
            await update.message.delete()
        except:
            pass
        
        # التحقق من الحد الأدنى 30 حرف
        if len(text) < 30:
            # حذف الرسالة السابقة
            if context.user_data.get('last_bot_message'):
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.user_data['last_bot_message']
                    )
                except:
                    pass
            
            sent_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"⚠️ **المنشور قصير جداً!**\n\n"
                    f"تم إدخال **{len(text)}** حرف فقط.\n"
                    f"الحد الأدنى: **30 حرف**\n\n"
                    f"📝 يرجى كتابة منشور أطول وأكثر فائدة.\n\n"
                    f"📌 للرجوع: /start"
                ),
                parse_mode='Markdown'
            )
            context.user_data['last_bot_message'] = sent_msg.message_id
            return
        
        # إذا كان صحيح - طلب العنوان
        context.user_data['post_content'] = text
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📝 **اكتب عنوان للمنشور:**\n\n"
                "مثال: نصيحة في الرياضيات"
            ),
            parse_mode='Markdown'
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        context.user_data.pop('awaiting_post_content', None)
        context.user_data['awaiting_post_title'] = True
        return
    
    # ========== معالجة استلام عنوان المنشور ==========
    if context.user_data.get('awaiting_post_title'):
        # حذف رسالة المستخدم
        try:
            await update.message.delete()
        except:
            pass
        
        title = text
        content = context.user_data.get('post_content')
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        # حفظ في قاعدة البيانات كمنشور
        item_id = add_to_library(
            title=title,
            description=content,
            file_id='text_content',  # قيمة وهمية للمنشورات النصية
            file_type='text',
            category='منشورات',
            uploader_id=user.id,
            uploader_name=user.full_name,
            approved=0,
            content_type='post'
        )
        
        safe_title = escape_markdown(title)
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ **تم رفع منشورك بنجاح!**\n\n"
                f"📝 **العنوان:** {safe_title}\n"
                f"🆔 **رقم المنشور:** {item_id}\n\n"
                f"⏳ المنشور الآن بانتظار موافقة الإدارة\\.\n"
                f"سنخبرك عند الموافقة عليه\\.\n\n"
                f"🌟 **شكراً لمساهمتك!**\n\n"
                f"📌 للرجوع: /start"
            ),
            parse_mode='Markdown'
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        
        # إشعار الأدمن بالمنشور الجديد
        from advanced_features import notify_admins_new_content
        await notify_admins_new_content(
            context=context,
            item_id=item_id,
            title=title,
            content_type='post',
            uploader_name=user.full_name
        )
        
        # مسح البيانات المؤقتة
        context.user_data.pop('post_content', None)
        context.user_data.pop('awaiting_post_title', None)
        
        logger.info(f"رفع منشور جديد: {title} بواسطة {user.id}")
        return
    
    # ========== معالجة استلام محتوى المقال ==========
    if context.user_data.get('awaiting_article_content'):
        # حذف رسالة المستخدم
        try:
            await update.message.delete()
        except:
            pass
        
        # التحقق من الحد الأدنى 100 حرف
        if len(text) < 100:
            # حذف الرسالة السابقة
            if context.user_data.get('last_bot_message'):
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.user_data['last_bot_message']
                    )
                except:
                    pass
            
            sent_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"⚠️ **المقال قصير جداً!**\n\n"
                    f"تم إدخال **{len(text)}** حرف فقط.\n"
                    f"الحد الأدنى: **100 حرف**\n\n"
                    f"📝 يرجى كتابة مقال أطول وأكثر تفصيلاً.\n\n"
                    f"📌 للرجوع: /start"
                ),
                parse_mode='Markdown'
            )
            context.user_data['last_bot_message'] = sent_msg.message_id
            return
        
        # إذا كان صحيح - طلب العنوان
        context.user_data['article_content'] = text
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "📝 **اكتب عنوان للمقال:**\n\n"
                "مثال: أهمية الرياضيات في حياتنا"
            ),
            parse_mode='Markdown'
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        context.user_data.pop('awaiting_article_content', None)
        context.user_data['awaiting_article_title'] = True
        return
    
    # ========== معالجة استلام عنوان المقال ==========
    if context.user_data.get('awaiting_article_title'):
        # حذف رسالة المستخدم
        try:
            await update.message.delete()
        except:
            pass
        
        title = text
        content = context.user_data.get('article_content')
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        # حفظ في قاعدة البيانات كمقال
        item_id = add_to_library(
            title=title,
            description=content,
            file_id='text_content',  # قيمة وهمية للمقالات النصية
            file_type='text',
            category='مقالات',
            uploader_id=user.id,
            uploader_name=user.full_name,
            approved=0,
            content_type='article'
        )
        
        safe_title = escape_markdown(title)
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ **تم رفع مقالك بنجاح!**\n\n"
                f"📝 **العنوان:** {safe_title}\n"
                f"🆔 **رقم المقال:** {item_id}\n\n"
                f"⏳ المقال الآن بانتظار موافقة الإدارة\\.\n"
                f"سنخبرك عند الموافقة عليه\\.\n\n"
                f"🌟 **شكراً لمساهمتك!**\n\n"
                f"📌 للرجوع: /start"
            ),
            parse_mode='Markdown'
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        
        # إشعار الأدمن بالمقال الجديد
        from advanced_features import notify_admins_new_content
        await notify_admins_new_content(
            context=context,
            item_id=item_id,
            title=title,
            content_type='article',
            uploader_name=user.full_name
        )
        
        # مسح البيانات المؤقتة
        context.user_data.pop('article_content', None)
        context.user_data.pop('awaiting_article_title', None)
        
        logger.info(f"رفع مقال جديد: {title} بواسطة {user.id}")
        return
    
    # ========== معالجة استلام وصف الكتاب ==========
    if context.user_data.get('awaiting_library_desc'):
        # حذف رسالة الوصف
        try:
            await update.message.delete()
        except:
            pass
        
        desc = text
        title = context.user_data.get('upload_title')
        content_type = context.user_data.get('content_type', 'book')
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        # حفظ جميع الملفات في قاعدة البيانات
        upload_files = context.user_data.get('upload_files', [])
        
        if not upload_files:
            # في حالة ملف واحد قديم (للتوافق مع النظام القديم)
            file_id = context.user_data.get('upload_file_id')
            file_type = context.user_data.get('upload_file_type', 'document')
            
            if file_id:
                item_id = add_to_library(
                    title=title,
                    description=desc,
                    file_id=file_id,
                    file_type=file_type,
                    category='عام',
                    uploader_id=user.id,
                    uploader_name=user.full_name,
                    approved=0,
                    content_type=content_type
                )
                saved_count = 1
        else:
            # حفظ عنصر واحد في المكتبة وإضافة جميع الملفات له
            # إضافة العنصر الرئيسي للمكتبة
            first_file = upload_files[0]
            item_id = add_to_library(
                title=title,
                description=desc,
                file_id=first_file['file_id'],
                file_type=first_file['file_type'],
                category='عام',
                uploader_id=user.id,
                uploader_name=user.full_name,
                approved=0,
                content_type=content_type
            )
            
            # إضافة جميع الملفات إلى جدول library_files
            from database import add_library_file
            for idx, file_info in enumerate(upload_files):
                add_library_file(
                    library_item_id=item_id,
                    file_id=file_info['file_id'],
                    file_type=file_info['file_type'],
                    file_order=idx,
                    caption=file_info.get('file_name', ''),
                    local_path=file_info.get('local_path')
                )
            
            # كتابة ملف ميتاداتا يحفظ كل التفاصيل
            try:
                os.makedirs(os.path.join('data', 'metadata', 'library'), exist_ok=True)
                metadata = {
                    'id': item_id,
                    'title': title,
                    'description': desc,
                    'category': 'عام',
                    'content_type': content_type,
                    'uploader_id': user.id,
                    'uploader_name': user.full_name,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'files': [
                        {
                            'file_id': f.get('file_id'),
                            'file_type': f.get('file_type'),
                            'file_name': f.get('file_name'),
                            'local_path': f.get('local_path')
                        } for f in upload_files
                    ]
                }
                with open(os.path.join('data', 'metadata', 'library', f'item_{item_id}.json'), 'w', encoding='utf-8') as fp:
                    json.dump(metadata, fp, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"فشل كتابة الميتاداتا للعنصر {item_id}: {e}")
            
            saved_count = len(upload_files)
        
        safe_title = escape_markdown(title)
        
        # رسالة النجاح
        if saved_count == 1:
            success_msg = (
                f"✅ **تم رفع ملفك بنجاح!**\n\n"
                f"📚 العنوان: **{safe_title}**\n\n"
            )
        else:
            success_msg = (
                f"✅ **تم رفع ملفاتك بنجاح!**\n\n"
                f"📚 العنوان: **{safe_title}**\n"
                f"📊 عدد الملفات: **{saved_count}**\n\n"
            )
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                success_msg +
                f"⏳ الملفات الآن بانتظار موافقة الإدارة\\.\n"
                f"سنخبرك عند الموافقة عليها\\.\n\n"
                f"🌟 شكراً لمساهمتك في إثراء المكتبة!\n\n"
                f"📌 للرجوع: /start"
            ),
            parse_mode='Markdown'
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        
        # إشعار الأدمن بالمحتوى الجديد
        from advanced_features import notify_admins_new_content
        await notify_admins_new_content(
            context=context,
            item_id=item_id,
            title=title,
            content_type=content_type,
            uploader_name=user.full_name,
            files_count=saved_count
        )
        
        # مسح البيانات المؤقتة
        context.user_data.pop('upload_files', None)
        context.user_data.pop('upload_file_id', None)
        context.user_data.pop('upload_file_type', None)
        context.user_data.pop('upload_title', None)
        context.user_data.pop('awaiting_library_desc', None)
        context.user_data.pop('content_type', None)
        
        logger.info(f"رفع {saved_count} ملف(ات): {title} بواسطة {user.id}")
        return
    
    # ========== إضافة مادة جديدة (أدمن) ==========
    if context.user_data.get('awaiting_new_subject_gidx') is not None:
        try:
            gidx = int(context.user_data.get('awaiting_new_subject_gidx'))
        except Exception:
            context.user_data.pop('awaiting_new_subject_gidx', None)
            return
        # حفظ الاسم مبدئياً
        if 'pending_subjects' not in context.user_data:
            context.user_data['pending_subjects'] = {}
        context.user_data['pending_subjects'][gidx] = text.strip()
        # اطلب اختيار الحالة
        try:
            await update.message.delete()
        except:
            pass
        rows = [[
            InlineKeyboardButton("✅ متوفر", callback_data=f'admin_bs_status_new_idx_{gidx}_a'),
            InlineKeyboardButton("🟨 جزئي", callback_data=f'admin_bs_status_new_idx_{gidx}_p'),
            InlineKeyboardButton("❌ غير متوفر", callback_data=f'admin_bs_status_new_idx_{gidx}_u'),
        ]]
        await update.message.reply_text(
            f"📘 {text}\n\nاختر الحالة:",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode='Markdown'
        )
        context.user_data.pop('awaiting_new_subject_gidx', None)
        return

    # ========== إرسال رسالة جماعية (أدمن) ==========
    if context.user_data.get('awaiting_broadcast'):
        if not is_admin(user.id):
            return
        
        users = get_all_users()
        success = 0
        fail = 0
        
        await update.message.reply_text(f"📤 جاري الإرسال لـ {len(users)} مستخدم...")
        
        safe_broadcast = escape_markdown(text)
        
        for uid in users:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"📢 **إعلان من إدارة المدرسة**\n\n{safe_broadcast}",
                    parse_mode='Markdown'
                )
                success += 1
            except:
                fail += 1
        
        await update.message.reply_text(
            f"✅ اكتمل الإرسال!\n\n"
            f"✔️ نجح: {success}\n"
            f"❌ فشل: {fail}",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_broadcast'] = False
        logger.info(f"إرسال جماعي: {success} نجح، {fail} فشل")
        return
    
    # رسالة افتراضية - حذف رسالة المستخدم
    try:
        await update.message.delete()
    except:
        pass
    
    # حذف الرسالة السابقة
    if context.user_data.get('last_bot_message'):
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=context.user_data['last_bot_message']
            )
        except:
            pass
    
    sent_msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "👋 مرحباً!\n\n"
            "استخدم /start للوصول للقائمة الرئيسية"
        ),
        parse_mode='Markdown'
    )
    context.user_data['last_bot_message'] = sent_msg.message_id

# ============== معالج الملفات ==============

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الملفات (PDF, صور, مستندات)"""
    user = update.effective_user
    
    # استقبال صورة الإعلان (أدمن)
    if context.user_data.get('awaiting_ad_image'):
        if not is_admin(user.id):
            return
        
        # التحقق من وجود صورة
        if not update.message.photo:
            await update.message.reply_text(
                "⚠️ يرجى إرسال صورة\n\n"
                "💡 أو اكتب 'skip' للتخطي",
                parse_mode='Markdown'
            )
            return
        
        from database import add_ad
        ad_title = context.user_data.get('ad_title')
        ad_content = context.user_data.get('ad_content')
        
        # الحصول على file_id لأعلى جودة صورة
        photo_file_id = update.message.photo[-1].file_id
        
        ad_id = add_ad(ad_title, ad_content, photo_file_id, user.id)
        safe_title = escape_markdown(ad_title)
        
        await update.message.reply_text(
            f"✅ **تم إضافة الإعلان بنجاح!**\n\n"
            f"🆔 **الرقم:** `{ad_id}`\n"
            f"📌 **العنوان:** {safe_title}\n"
            f"🖼️ **الصورة:** ✅ مرفقة\n\n"
            f"✅ الإعلان نشط وسيظهر لجميع المستخدمين الجدد\\.\n\n"
            f"🔧 استخدم /admin\\_panel لإدارة الإعلانات",
            parse_mode='Markdown'
        )
        
        context.user_data.pop('ad_title', None)
        context.user_data.pop('ad_content', None)
        context.user_data.pop('awaiting_ad_image', None)
        logger.info(f"إضافة إعلان {ad_id} مع صورة بواسطة {user.id}")
        return
    
    # رفع كتاب من مستخدم عادي
    if context.user_data.get('awaiting_library_file'):
        file = None
        file_type = 'document'
        
        # التحقق من نوع الملف
        if update.message.document:
            file = update.message.document
            file_type = 'document'
        elif update.message.photo:
            file = update.message.photo[-1]  # أعلى جودة
            file_type = 'photo'
        
        if not file:
            await update.message.reply_text("⚠️ يرجى إرسال ملف PDF أو صورة")
            return
        
        # حذف الملف الذي أرسله المستخدم
        try:
            await update.message.delete()
        except:
            pass
        
        # تنزيل الملف وحفظه محلياً ضمن مجلد منظم
        if 'upload_files' not in context.user_data:
            context.user_data['upload_files'] = []
        
        # تحديد المجلد حسب النوع
        base_dir = os.path.join('data', 'uploads')
        sub_dir = 'images' if file_type == 'photo' else 'documents'
        dest_dir = os.path.join(base_dir, sub_dir)
        os.makedirs(dest_dir, exist_ok=True)
        
        # تحديد اسم الملف مع تنقية
        if hasattr(file, 'file_name') and file.file_name:
            filename = sanitize_filename(file.file_name)
        else:
            # للصور لا يوجد اسم — ننشئ اسماً زمنياً
            filename = sanitize_filename(
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(context.user_data['upload_files']) + 1}.jpg"
            )
        
        # تنزيل عبر File API
        try:
            tg_file = await context.bot.get_file(file.file_id)
            local_path = unique_path(dest_dir, filename)
            await tg_file.download_to_drive(custom_path=local_path)
        except Exception as e:
            logger.error(f"فشل تنزيل الملف محلياً: {e}")
            local_path = None
        
        context.user_data['upload_files'].append({
            'file_id': file.file_id,
            'file_type': file_type,
            'file_name': os.path.basename(local_path) if local_path else filename,
            'local_path': local_path
        })
        
        files_count = len(context.user_data['upload_files'])
        
        # حذف الرسالة السابقة
        if context.user_data.get('last_bot_message'):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data['last_bot_message']
                )
            except:
                pass
        
        # عرض خيارات: إضافة مزيد أو إنهاء
        keyboard = [
            [InlineKeyboardButton("✅ إنهاء الرفع والمتابعة", callback_data='finish_upload')],
            [InlineKeyboardButton("❌ إلغاء", callback_data='cancel_upload')]
        ]
        
        sent_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"✅ **تم إضافة الملف!**\n\n"
                f"📊 **عدد الملفات:** {files_count}\n\n"
                f"📝 **الخيارات:**\n"
                f"• أرسل ملفاً آخر لإضافته\n"
                f"• أو اضِغط '✅ إنهاء الرفع' للمتابعة"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        context.user_data['last_bot_message'] = sent_msg.message_id
        return
    
    
    # رفع كتاب من أدمن
    if context.user_data.get('awaiting_admin_upload'):
        if not is_admin(user.id):
            return
        
        file = update.message.document or update.message.photo[-1] if update.message.photo else None
        if file:
            await update.message.reply_text("📝 اكتب عنوان الكتاب:")
            context.user_data['admin_file_id'] = file.file_id
            context.user_data['awaiting_admin_upload'] = False
            context.user_data['awaiting_admin_title'] = True

# ============== أوامر خاصة ==============

async def admin_secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر سري لتسجيل دخول الأدمن"""
    await update.message.reply_text(
        "🔐 **تسجيل دخول الأدمن**\n\n"
        "أرسل كلمة السر: `Admin_log`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_admin_password'] = True

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم الأدمن"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ ليس لديك صلاحية الوصول.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📰 إدارة الأخبار", callback_data='admin_news')],
        [InlineKeyboardButton("➕ إضافة خبر جديد", callback_data='add_news')],
        [InlineKeyboardButton("📢 إرسال إعلان جماعي", callback_data='send_news')],
        [InlineKeyboardButton("📚 تحديث حالة الكتب", callback_data='admin_books_status')],
        [InlineKeyboardButton("📖 إدارة المكتبة", callback_data='admin_library')],
        [InlineKeyboardButton("📊 إحصائيات تفصيلية", callback_data='detailed_stats')],
        [InlineKeyboardButton("👥 عدد المستخدمين", callback_data='list_users')],
    ]
    await update.message.reply_text(
        "🔧 **لوحة تحكم الأدمن**\n\nاختر العملية:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    logger.info(f"الأدمن {update.effective_user.id} دخل لوحة التحكم")

# أوامر الموافقة والرفض
async def approve_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الموافقة على كتاب"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ ليس لديك صلاحية.")
        return
    
    # الحصول على الـ ID من الأمر
    try:
        book_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "⚠️ استخدام خاطئ!\n\n"
            "الصيغة الصحيحة: `/approve 123`"
        )
        return
    
    # الحصول على معلومات الكتاب
    item = get_library_item(book_id)
    if not item:
        await update.message.reply_text("❌ لم يتم العثور على الكتاب.")
        return
    
    # الموافقة على الكتاب
    approve_library_item(book_id, update.effective_user.id)
    
    title = item[1]
    uploader_name = item[7]
    
    await update.message.reply_text(
        f"✅ **تمت الموافقة!**\n\n"
        f"📚 العنوان: {title}\n"
        f"👤 بواسطة: {uploader_name}\n\n"
        f"الكتاب الآن متاح في المكتبة!"
    )
    logger.info(f"الموافقة على كتاب {book_id} بواسطة {update.effective_user.id}")

async def reject_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رفض كتاب"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ ليس لديك صلاحية.")
        return
    
    # الحصول علم الـ ID من الأمر
    try:
        book_id = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(
            "⚠️ استخدام خاطئ!\n\n"
            "الصيغة الصحيحة: `/reject 123`"
        )
        return
    
    # الحصول على معلومات الكتاب
    item = get_library_item(book_id)
    if not item:
        await update.message.reply_text("❌ لم يتم العثور على الكتاب.")
        return
    
    title = item[1]
    
    # حذف الكتاب
    delete_library_item(book_id)
    
    await update.message.reply_text(
        f"❌ **تم رفض الكتاب**\n\n"
        f"📚 العنوان: {title}\n\n"
        f"تم حذف الكتاب من قاعدة البيانات."
    )
    logger.info(f"رفض كتاب {book_id} بواسطة {update.effective_user.id}")

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على استفسار مستخدم (للأدمن فقط)"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ ليس لديك صلاحية.")
        return
    
    # التحقق من وجود معرف المستخدم والرسالة
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ **استخدام خاطئ!**\n\n"
            "📖 **الصيغة الصحيحة:**\n"
            "`/reply [user_id] [رسالتك]`\n\n"
            "💡 **مثال:**\n"
            "`/reply 123456789 شكراً على استفسارك, الإجابة هي...`",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        reply_text = ' '.join(context.args[1:])
        
        # إرسال الرد للمستخدم
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "╔═════════════════════════╗\n"
                "║   📨 **رد من الإدارة**   ║\n"
                "╚═════════════════════════╝\n\n"
                f"{reply_text}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "💬 للاستفسار مرة أخرى: /start ثم '💬 استفسار'"
            ),
            parse_mode='Markdown'
        )
        
        # تأكيد للأدمن
        await update.message.reply_text(
            f"✅ **تم إرسال الرد بنجاح!**\n\n"
            f"🎯 إلى المستخدم: `{user_id}`\n"
            f"📨 الرسالة: {reply_text}",
            parse_mode='Markdown'
        )
        
        logger.info(f"رد من الأدمن {update.effective_user.id} إلى المستخدم {user_id}")
        
    except ValueError:
        await update.message.reply_text(
            "❌ **خطأ!**\n\n"
            "معرف المستخدم يجب أن يكون رقماً.",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ **فشل إرسال الرسالة**\n\n"
            f"قد يكون المستخدم حظر البوت أو حذف المحادثة.\n\n"
            f"🔍 الخطأ: {str(e)}",
            parse_mode='Markdown'
        )
        logger.error(f"فشل إرسال الرد إلم {user_id}: {e}")

# معالج تسجيل دخول الأدمن
async def process_admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة تسجيل دخول الأدمن"""
    text = update.message.text.strip()
    
    # مرحلة 1: كلمة السر
    if context.user_data.get('awaiting_admin_password'):
        if text == "Admin_log":
            # حذف رسالة كلمة السر
            try:
                await update.message.delete()
            except:
                pass
            
            await update.message.reply_text("✅ تم التأكيد.\n\nالآن أرسل اسمك:")
            context.user_data['awaiting_admin_password'] = False
            context.user_data['awaiting_admin_name'] = True
        else:
            await update.message.reply_text("❌ كلمة السر خاطئة.")
        return
    
    # مرحلة 2: الاسم
    if context.user_data.get('awaiting_admin_name'):
        # حذف رسالة الاسم
        try:
            await update.message.delete()
        except:
            pass
        
        context.user_data['admin_name_input'] = text
        await update.message.reply_text("الآن أرسل إيميلك:")
        context.user_data['awaiting_admin_name'] = False
        context.user_data['awaiting_admin_email'] = True
        return
    
    # مرحلة 3: الإيميل
    if context.user_data.get('awaiting_admin_email'):
        # حذف رسالة الإيميل
        try:
            await update.message.delete()
        except:
            pass
        
        name = context.user_data.get('admin_name_input')
        email = text
        
        if name == Config.ADMIN_NAME and email == Config.ADMIN_EMAIL:
            add_admin(update.effective_user.id)
            await update.message.reply_text(
                "🎉 تم تسجيل دخولك كأدمن!\n\n"
                "استخدم /admin_panel لفتح لوحة التحكم"
            )
            logger.info(f"تسجيل دخول أدمن: {update.effective_user.id}")
        else:
            await update.message.reply_text("❌ البيانات غير متطابقة.")
        
        context.user_data.pop('awaiting_admin_email', None)
        context.user_data.pop('admin_name_input', None)
        return

# ============== APScheduler - المهام الآلية (للإنتاج) ==============

async def scrape_new_messages_job():
    """
    🔍 مهمة "الباحث السريع" - تعمل كل 5 دقائق
    تسحب الرسائل الجديدة من القناة وتضيفها لقاعدة البيانات
    (متوافقة مع APScheduler - بدون context)
    """
    try:
        logger.info("="*60)
        logger.info("🔍 بدء مهمة التحديث الآلي (APScheduler)...")
        logger.info("="*60)
        
        # سحب الرسائل من آخر 10 دقائق
        new_documents = await scraper.scrape_recent_messages(minutes=10)
        
        if new_documents:
            # إضافتها لقاعدة البيانات
            added = vector_store.add_new_messages(new_documents)
            if added > 0:
                logger.info(f"✅ تم تحديث قاعدة البيانات بـ {added} رسالة جديدة")
        else:
            logger.info("ℹ️ لا توجد رسائل جديدة")
        
        logger.info("="*60)
    
    except Exception as e:
        logger.error(f"❌ خطأ في مهمة التحديث الآلي: {e}")


async def prune_old_messages_job():
    """
    🧹 مهمة "عامل النظافة" - تعمل مرة يومياً (عند 3 فجراً)
    تحذف الرسائل الأقدم من 365 يوم
    (متوافقة مع APScheduler - بدون context)
    """
    try:
        logger.info("="*60)
        logger.info("🧹 بدء مهمة تنظيف الرسائل القديمة (APScheduler)...")
        logger.info("="*60)
        
        deleted = vector_store.delete_old_messages(days=365)
        
        if deleted > 0:
            logger.info(f"✅ تم حذف {deleted} رسالة قديمة")
        else:
            logger.info("ℹ️ لا توجد رسائل قديمة لحذفها")
        
        logger.info("="*60)
    
    except Exception as e:
        logger.error(f"❌ خطأ في مهمة التنظيف: {e}")


# ============== Main ==============

def main():
    """تشغيل البوت"""
    init_db()
    
    if not Config.BOT_TOKEN or Config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ خطأ: Token غير موجود")
        print("\n⚠️ يرجى إضافة Bot Token في ملف .env\n")
        return
    
    # بناء قاعدة البيانات قبل التشغيل (إذا لزم الأمر)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        db_ready = loop.run_until_complete(setup_database_once())
        if not db_ready:
            logger.critical("!!! فشل إعداد قاعدة البيانات. البوت سيعمل بميزات محدودة أو قد يتوقف.")
            # يمكنك إيقاف البوت تماماً إذا أردت
            # return
    except Exception as e:
        logger.warning(f"تحذير في بناء قاعدة البيانات: {e}")
    # لا نغلق loop لأن البوت سيستخدمه
    
    # إنشاء التطبيق مع إعدادات timeout محسّنة
    from telegram.request import HTTPXRequest
    
    # زيادة وقت الانتظار للملفات الكبيرة
    request = HTTPXRequest(
        connection_pool_size=8,
        connect_timeout=30.0,      # 30 ثانية للاتصال
        read_timeout=60.0,         # 60 ثانية للقراءة
        write_timeout=120.0,       # 120 ثانية للكتابة (رفع الملفات)
        pool_timeout=30.0
    )
    
    application = Application.builder() \
        .token(Config.BOT_TOKEN) \
        .request(request) \
        .build()
    
    # === 📅 APScheduler - جدولة المهام الآلية (للإنتاج) ===
    # ملاحظة: سيتم تشغيل scheduler بعد بدء التطبيق
    async def post_init(application):
        """تشغيل APScheduler بعد بدء التطبيق"""
        scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Riyadh'))
        
        # 🔍 مهمة 1: الباحث السريع - كل 5 دقائق
        scheduler.add_job(
            scrape_new_messages_job,
            'interval',
            minutes=5,
            id='scraper_job',
            replace_existing=True,
            max_instances=1
        )
        logger.info("✅ تم جدولة مهمة 'الباحث السريع' (كل 5 دقائق) - APScheduler")
        
        # 🧹 مهمة 2: عامل النظافة - يومياً عند 3 فجراً
        scheduler.add_job(
            prune_old_messages_job,
            CronTrigger(hour=3, minute=0, timezone=pytz.timezone('Asia/Riyadh')),
            id='cleanup_job',
            replace_existing=True,
            max_instances=1
        )
        logger.info("✅ تم جدولة مهمة 'عامل النظافة' (يومياً 3:00ص بتوقيت السعودية) - APScheduler")
        
        # تشغيل المجدول (الآن event loop يعمل)
        scheduler.start()
        logger.info("✅ تم تشغيل APScheduler بنجاح")
        
        # حفظ scheduler في application لاستخدامه لاحقاً
        application.bot_data['scheduler'] = scheduler
    
    # إضافة post_init callback
    application.post_init = post_init

    # إضافة معالج أخطاء عام لتجنب توقف التطبيق دون تسجيل مناسب
    async def error_handler(update, context):
        logger.exception("Unhandled exception while processing update", exc_info=context.error)

    application.add_error_handler(error_handler)
    
    # الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin_secret", admin_secret))
    application.add_handler(CommandHandler("admin_panel", admin_panel))
    application.add_handler(CommandHandler("approve", approve_book))
    application.add_handler(CommandHandler("reject", reject_book))
    application.add_handler(CommandHandler("reply", reply_to_user))
    
    # الأزرار
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # الرسائل - أولوية للكيبورد ثم معالجات أخرى
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        lambda u, c: (
            process_admin_login(u, c) if (
                c.user_data and (
                    c.user_data.get('awaiting_admin_password') or 
                    c.user_data.get('awaiting_admin_name') or 
                    c.user_data.get('awaiting_admin_email')
                )
            ) else (
                keyboard_handler(u, c) if u.message and u.message.text in [
                    "📰 الأخبار", "📚 حالة الكتب", "📖 المكتبة", 
                    "📚 كتبي", "⭐ المفضلة", "🔔 إشعارات",
                    "❓ مساعدة", "💬 استفسار", "❓ طرح استفسار",
                    "❓ طرح استفسار ذكي", "📊 آخر 5 أخبار رسمية"
                ] else message_handler(u, c)
            )
        )
    ))
    
    # الملفات
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, document_handler))
    
    logger.info("=" * 60)
    logger.info("🚀 البوت يعمل!")
    logger.info(f"👤 أدمن: {Config.ADMIN_NAME}")
    logger.info("=" * 60)
    
    print("\n✅ البوت يعمل الآن!")
    print("استخدم /start في تليجرام")
    print("للأدمن: /admin_secret\n")
    
    # تشغيل Webhook إذا كان WEBHOOK_URL مضبوطاً (ضروري للاستضافات مثل pella)
    if getattr(Config, 'WEBHOOK_URL', None) and Config.WEBHOOK_URL != "https://your-domain.com/webhook":
        full_webhook = f"{Config.WEBHOOK_URL.rstrip('/')}/{Config.BOT_TOKEN}"
        application.run_webhook(
            listen=Config.HOST,
            port=Config.PORT,
            url_path=Config.BOT_TOKEN,
            webhook_url=full_webhook,
            drop_pending_updates=True
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
