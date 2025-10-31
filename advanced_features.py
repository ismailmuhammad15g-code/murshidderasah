"""
ميزات متقدمة للبوت - التقييمات، المفضلة، الإشعارات
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import *
import logging
import html

logger = logging.getLogger(__name__)

# ========== وظيفة إشعار الأدمن ==========

async def notify_admins_new_content(context, item_id, title, content_type, uploader_name, files_count=1):
    """إرسال إشعار للأدمن عند رفع محتوى جديد"""
    from database import get_all_admins
    
    admins = get_all_admins()
    
    # تحديد الإيموجي والنوع
    type_info = {
        'book': ('📚', 'كتاب'),
        'image': ('🖼️', 'صورة'),
        'article': ('📝', 'مقال'),
        'post': ('📣', 'منشور')
    }
    
    emoji, type_name = type_info.get(content_type, ('📄', 'محتوى'))
    
    # إعداد نص الإشعار
    notification_text = (
        f"🔔 **محتوى جديد بانتظار المراجعة**\n\n"
        f"{emoji} **النوع:** {type_name}\n"
        f"📖 **العنوان:** {title}\n"
        f"👤 **المرسل:** {uploader_name}\n"
    )
    
    if files_count > 1:
        notification_text += f"📊 **عدد الملفات:** {files_count}\n"
    
    notification_text += (
        f"🆔 **رقم المحتوى:** `{item_id}`\n\n"
        f"⏳ يحتاج إلى مراجعتك"
    )
    
    # أزرار الموافقة والرفض
    keyboard = [
        [
            InlineKeyboardButton("✅ موافق", callback_data=f'approve_{item_id}'),
            InlineKeyboardButton("❌ رفض", callback_data=f'reject_{item_id}')
        ],
        [InlineKeyboardButton("👁️ معاينة", callback_data=f'preview_admin_{item_id}')]
    ]
    
    # إرسال الإشعار لجميع الأدمن
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"فشل إرسال إشعار للأدمن {admin_id}: {e}")

# ========== وظائف التقييمات ==========

def get_rating_keyboard(book_id):
    """الحصول على لوحة تقييم الكتاب"""
    keyboard = [
        [
            InlineKeyboardButton("⭐", callback_data=f'rate_{book_id}_1'),
            InlineKeyboardButton("⭐⭐", callback_data=f'rate_{book_id}_2'),
            InlineKeyboardButton("⭐⭐⭐", callback_data=f'rate_{book_id}_3'),
        ],
        [
            InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f'rate_{book_id}_4'),
            InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f'rate_{book_id}_5'),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data=f'view_book_{book_id}')]
    ]
    return InlineKeyboardMarkup(keyboard)

def format_rating_stars(rating):
    """تحويل الرقم إلى نجوم"""
    full_stars = int(rating)
    half_star = 1 if (rating - full_stars) >= 0.5 else 0
    empty_stars = 5 - full_stars - half_star
    
    return "⭐" * full_stars + "✨" * half_star + "☆" * empty_stars

def get_book_details_text(item):
    """الحصول على نص تفاصيل المحتوى مع التقييمات"""
    from main import escape_markdown
    
    # Indexes based on library table structure:
    # 0:id, 1:title, 2:description, 3:file_id, 4:file_type, 5:content_type,
    # 6:category, 7:uploader_id, 8:uploader_name, 9:upload_date, 10:approved, 11:approved_by,
    # 12:downloads, 13:views, 14:total_rating, 15:rating_count
    book_id = item[0]
    title = escape_markdown(item[1])
    description = item[2] or "لا يوجد وصف"
    uploader_name = escape_markdown(item[8])
    category = escape_markdown(item[6] if len(item) > 6 else "عام")
    downloads = item[12] if len(item) > 12 else 0
    views = item[13] if len(item) > 13 else 0
    content_type = item[5] if len(item) > 5 else 'book'
    
    # حساب التقييم
    avg_rating, rating_count = get_book_rating(book_id)
    rating_text = format_rating_stars(avg_rating) if rating_count > 0 else "لم يُقيّم بعد"
    
    # تحديد نوع المحتوى والأيقونة والعنوان
    content_icons = {
        'article': '📝',
        'post': '📣',
        'book': '📖',
        'image': '🖼️'
    }
    
    content_names = {
        'article': 'المقال',
        'post': 'المنشور',
        'book': 'الكتاب',
        'image': 'الصورة'
    }
    
    icon = content_icons.get(content_type, '📖')
    name = content_names.get(content_type, 'الكتاب')
    
    # للمقالات والمنشورات - عرض المحتوى كـ quote
    if content_type in ['article', 'post']:
        # حماية الوصف/المحتوى من أخطاء Markdown
        safe_description = escape_markdown(description)
        
        text = (
            f"{icon} **تفاصيل {name}**\n\n"
            f"📚 **العنوان:** {title}\n\n"
        )
        
        # عرض المحتوى كـ quote مع خلفية
        if content_type == 'article':
            text += f"📝 **المحتوى:**\n\n"
        else:
            text += f"📣 **المنشور:**\n\n"
        
        # تقسيم المحتوى إلى أسطر وإضافة > لكل سطر
        content_lines = safe_description.split('\n')
        for line in content_lines:
            if line.strip():
                text += f"> {line}\n"
        
        text += (
            f"\n📑 **الفئة:** {category}\n"
            f"👤 **كتب بواسطة:** {uploader_name}\n"
            f"⭐ **التقييم:** {rating_text}"
        )
    else:
        # للكتب والصور - العرض العادي
        safe_description = escape_markdown(description)
        text = (
            f"{icon} **تفاصيل {name}**\n\n"
            f"📚 **العنوان:** {title}\n\n"
            f"📝 **الوصف:** {safe_description}\n\n"
            f"📑 **الفئة:** {category}\n"
            f"👤 **رفع بواسطة:** {uploader_name}\n"
            f"⭐ **التقييم:** {rating_text}"
        )
    
    if rating_count > 0:
        text += f" ({avg_rating:.1f}/5\\.0 من {rating_count} تقييم)\n"
    else:
        text += "\n"
    
    text += f"👁️ **عدد المشاهدات:** {views}\n"
    
    # عرض التحميلات فقط للكتب والصور
    if content_type not in ['article', 'post']:
        text += f"📥 **عدد التحميلات:** {downloads}\n"
    
    text += "\n"
    
    # إضافة بعض المراجعات
    reviews = get_book_reviews(book_id, limit=3)
    if reviews:
        text += "💬 **آخر المراجعات:**\n"
        for review in reviews:
            rating = review[0]
            review_text = review[1]
            reviewer = escape_markdown(review[3])
            text += f"• {format_rating_stars(rating)} - {reviewer}\n"
            if review_text:
                safe_review = escape_markdown(review_text[:50])
                text += f"  \"{safe_review}\\.\\.\\.\"\n"
        text += "\n"
    
    return text

# ========== وظائف الفئات ==========

def get_categories_keyboard():
    """الحصول على لوحة الفئات"""
    categories_data = get_categories()
    keyboard = []
    
    # الفئات الرئيسية
    main_categories = {
        "رياضيات": "📐",
        "علوم": "🔬",
        "لغة عربية": "📝",
        "لغة إنجليزية": "🇬🇧",
        "دين": "☪️",
        "تاريخ": "📜",
        "جغرافيا": "🌍",
        "عام": "📚"
    }
    
    # إضافة الفئات الموجودة
    for cat, count in categories_data:
        emoji = main_categories.get(cat, "📚")
        keyboard.append([InlineKeyboardButton(
            f"{emoji} {cat} ({count})",
            callback_data=f'category_{cat}'
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data='library')])
    return InlineKeyboardMarkup(keyboard)

# ========== وظائف الإشعارات ==========

async def send_notification_to_user(context, user_id, title, message, notification_type):
    """إرسال إشعار للمستخدم"""
    try:
        # حفظ في قاعدة البيانات
        add_notification(user_id, title, message, notification_type)
        
        # إرسال عبر التليجرام
        notification_icons = {
            'book_approved': '✅',
            'book_rejected': '❌',
            'admin_reply': '💬',
            'new_book': '📚',
            'reminder': '⏰',
            'news': '📢'
        }
        
        icon = notification_icons.get(notification_type, '🔔')
        
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                f"{icon} **{title}**\n\n"
                f"{message}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔔 للرجوع للقائمة: /start"
            ),
            parse_mode='Markdown'
        )
        return True
    except Exception as e:
        return False

def format_notification_text(notifications):
    """تنسيق نص الإشعارات"""
    if not notifications:
        return "🔔 **الإشعارات**\n\n📭 لا توجد إشعارات حالياً."
    
    text = "🔔 **إشعاراتك**\n\n"
    
    for notif in notifications[:10]:
        notif_id = notif[0]
        title = notif[1]
        message = notif[2][:50] + "..." if len(notif[2]) > 50 else notif[2]
        created_at = notif[3]
        
        notification_icons = {
            'book_approved': '✅',
            'book_rejected': '❌',
            'admin_reply': '💬',
            'new_book': '📚',
            'reminder': '⏰',
            'news': '📢'
        }
        
        icon = notification_icons.get(notif[4], '🔔')
        
        text += f"{icon} **{title}**\n"
        text += f"   {message}\n"
        text += f"   🕐 {created_at}\n\n"
    
    return text

# ========== وظائف البحث المتقدم ==========

def get_advanced_search_keyboard():
    """لوحة البحث المتقدم"""
    keyboard = [
        [InlineKeyboardButton("🔍 بحث بالعنوان", callback_data='search_by_title')],
        [InlineKeyboardButton("📑 تصفح حسب الفئة", callback_data='browse_categories')],
        [InlineKeyboardButton("🔥 الأكثر شعبية", callback_data='popular_books')],
        [InlineKeyboardButton("⭐ الأعلى تقييماً", callback_data='top_rated_books')],
        [InlineKeyboardButton("🔙 الرجوع", callback_data='library')]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== وظائف مساعدة ==========

def get_category_emoji(category):
    """الحصول على emoji الفئة"""
    emojis = {
        "رياضيات": "📐",
        "علوم": "🔬",
        "لغة عربية": "📝",
        "لغة إنجليزية": "🇬🇧",
        "دين": "☪️",
        "تاريخ": "📜",
        "جغرافيا": "🌍",
        "عام": "📚"
    }
    return emojis.get(category, "📚")

def format_book_list(books, show_category=True):
    """تنسيق قائمة الكتب"""
    if not books:
        return "📚 لا توجد كتب متاحة."
    
    text = ""
    for idx, book in enumerate(books[:10], 1):
        book_id = book[0]
        title = book[1]
        
        # التعامل مع أطوال مختلفة للصفوف
        if len(book) >= 7:
            category = book[2] if show_category else None
            downloads = book[3]
            total_rating = book[4] if len(book) > 4 else 0
            rating_count = book[5] if len(book) > 5 else 0
        else:
            category = None
            downloads = book[2] if len(book) > 2 else 0
            total_rating = 0
            rating_count = 0
        
        avg_rating = (total_rating / rating_count) if rating_count > 0 else 0
        rating_stars = format_rating_stars(avg_rating) if rating_count > 0 else "☆☆☆☆☆"
        
        text += f"{idx}. **{title}**\n"
        if category and show_category:
            text += f"   {get_category_emoji(category)} {category} | "
        else:
            text += "   "
        text += f"{rating_stars} | 📥 {downloads}\n\n"
    
    return text

# ========== وظائف معرض الصور ==========

async def show_book_details_with_gallery(query, context, book_id):
    """عرض تفاصيل الكتاب مع معرض الصور"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from database import get_library_item, get_library_files, is_favorite, user_has_rated, increment_views
    
    item = get_library_item(book_id)
    if not item:
        await query.edit_message_text("❌ لم يتم العثور على الكتاب.")
        return
    
    # زيادة عداد المشاهدات
    increment_views(book_id)
    
    # الحصول على جميع الملفات
    files = get_library_files(book_id)
    
    # إذا كان هناك عدة ملفات، أرسلها كـ media group
    if len(files) > 1:
        media_group = []
        
        for idx, (file_id, file_type, caption) in enumerate(files):
            if file_type == 'photo':
                from telegram import InputMediaPhoto
                media_item = InputMediaPhoto(
                    media=file_id,
                    caption=f"📸 صورة {idx+1}/{len(files)}" if idx == 0 else None
                )
                media_group.append(media_item)
        
        # إرسال المعرض إذا كان هناك صور
        if media_group:
            await context.bot.send_media_group(
                chat_id=query.from_user.id,
                media=media_group
            )
    
    # تحديد وضع العرض حسب نوع المحتوى
    content_type = item[5] if len(item) > 5 else 'book'
    parse_mode = 'Markdown'

    # عرض تفاصيل المحتوى
    if content_type in ['article', 'post']:
        # HTML منسق بأسلوب blockquote لكل المقالات/المنشورات
        title = html.escape(item[1])
        description = html.escape(item[2] or 'لا يوجد محتوى')
        uploader_name = html.escape(item[8])
        category = html.escape(item[6] if len(item) > 6 else 'عام')
        views = item[13] if len(item) > 13 else 0
        text = (
            f"<b>{'📝' if content_type=='article' else '📣'} {title}</b>\n\n"
            f"<blockquote>{description}</blockquote>\n\n"
            f"<i>📂 {category} • 👁️ {views} مشاهدة • ✍️ {uploader_name}</i>"
        )
        parse_mode = 'HTML'
    else:
        # للكتب/الصور نستخدم النص القديم Markdown
        text = get_book_details_text(item)
        # إضافة معلومات عن الملفات
        if files:
            text += f"\n📎 **الملفات المرفقة:** {len(files)} ملف\n"

    # بناء الأزرار
    keyboard = []

    # زر عرض المعرض
    if len(files) > 0:
        keyboard.append([InlineKeyboardButton(
            f"🖼️ عرض المعرض ({len(files)} ملف)",
            callback_data=f'show_gallery_{book_id}'
        )])

    # زر التحميل
    if files:
        keyboard.append([InlineKeyboardButton(
            "📥 تحميل جميع الملفات",
            callback_data=f'download_all_{book_id}'
        )])

    # بقية الأزرار (المفضلة، التقييم، الخ)
    is_fav = is_favorite(query.from_user.id, book_id)
    has_rated = user_has_rated(book_id, query.from_user.id) if content_type not in ['article', 'post'] else True

    if is_fav:
        keyboard.append([InlineKeyboardButton("⭐ إزالة من المفضلة", callback_data=f'unfav_{book_id}')])
    else:
        keyboard.append([InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f'fav_{book_id}')])

    if content_type not in ['article', 'post'] and not has_rated:
        keyboard.append([InlineKeyboardButton("⭐ قيّم هذا الكتاب", callback_data=f'rate_book_{book_id}')])

    keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data='library_browse')])

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=parse_mode
    )

async def show_gallery_handler(query, context, book_id):
    """عرض معرض الصور بشكل جميل"""
    from telegram import InputMediaPhoto
    from database import get_library_files
    
    files = get_library_files(book_id)
    
    if not files:
        await query.answer("⚠️ لا توجد ملفات لعرضها", show_alert=True)
        return
    
    # تجميع الصور والمستندات
    photos = []
    documents = []
    
    for idx, (file_id, file_type, caption) in enumerate(files):
        if file_type == 'photo':
            photos.append((file_id, caption))
        else:
            documents.append((file_id, caption))
    
    # إرسال الصور كمعرض
    if photos:
        media_group = []
        for idx, (file_id, caption) in enumerate(photos):
            media_item = InputMediaPhoto(
                media=file_id,
                caption=f"🖼️ الصورة {idx+1}/{len(photos)}\n{caption}" if idx == 0 else None
            )
            media_group.append(media_item)
        
        # إرسال المعرض
        await context.bot.send_media_group(
            chat_id=query.from_user.id,
            media=media_group
        )
        
        await query.answer(f"✅ تم إرسال {len(photos)} صورة", show_alert=False)
    
    # إرسال المستندات
    if documents:
        for file_id, caption in documents:
            await context.bot.send_document(
                chat_id=query.from_user.id,
                document=file_id,
                caption=caption or "📎 مرفق"
            )

async def download_all_files_handler(query, context, book_id):
    """تحميل جميع ملفات الكتاب"""
    from database import get_library_files, increment_downloads
    
    files = get_library_files(book_id)
    
    if not files:
        await query.answer("⚠️ لا توجد ملفات للتحميل", show_alert=True)
        return
    
    await query.answer(f"📥 جاري إرسال {len(files)} ملف...")
    
    # زيادة عداد التحميلات
    increment_downloads(book_id)
    
    # إرسال كل ملف
    for idx, (file_id, file_type, caption) in enumerate(files, 1):
        try:
            if file_type == 'photo':
                await context.bot.send_photo(
                    chat_id=query.from_user.id,
                    photo=file_id,
                    caption=f"📸 الملف {idx}/{len(files)}\n{caption or ''}"
                )
            else:
                await context.bot.send_document(
                    chat_id=query.from_user.id,
                    document=file_id,
                    caption=f"📎 الملف {idx}/{len(files)}\n{caption or ''}"
                )
        except Exception as e:
            print(f"خطأ في إرسال الملف {idx}: {e}")
    
    # رسالة تأكيد
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text=f"✅ تم إرسال جميع الملفات ({len(files)} ملف)"
    )
