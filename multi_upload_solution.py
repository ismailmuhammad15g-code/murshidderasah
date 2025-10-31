"""
حل مشكلة رفع وعرض ملفات متعددة في البوت
============================================
هذا الملف يحتوي على التعديلات اللازمة لدعم رفع عدة ملفات وعرضها كمعرض
"""

# ============== 1. تعديلات قاعدة البيانات ==============
def update_database_for_multi_files():
    """
    إضافة جدول جديد لحفظ ملفات متعددة لكل كتاب
    """
    import sqlite3
    
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    
    # إنشاء جدول للملفات المتعددة
    c.execute('''CREATE TABLE IF NOT EXISTS library_files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  library_item_id INTEGER,
                  file_id TEXT,
                  file_type TEXT,
                  file_order INTEGER DEFAULT 0,
                  caption TEXT,
                  FOREIGN KEY(library_item_id) REFERENCES library(id) ON DELETE CASCADE)''')
    
    # نقل الملفات الموجودة إلى الجدول الجديد
    c.execute('''INSERT INTO library_files (library_item_id, file_id, file_type, file_order)
                 SELECT id, file_id, file_type, 0
                 FROM library
                 WHERE file_id IS NOT NULL AND file_id != '' AND file_id != 'text_content' ''')
    
    conn.commit()
    conn.close()
    print("✅ تم تحديث قاعدة البيانات لدعم الملفات المتعددة")

# ============== 2. دوال قاعدة البيانات الجديدة ==============

def add_library_file(library_item_id, file_id, file_type, file_order=0, caption=""):
    """إضافة ملف لعنصر في المكتبة"""
    import sqlite3
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''INSERT INTO library_files (library_item_id, file_id, file_type, file_order, caption)
                 VALUES (?, ?, ?, ?, ?)''',
              (library_item_id, file_id, file_type, file_order, caption))
    conn.commit()
    conn.close()

def get_library_files(library_item_id):
    """الحصول على جميع ملفات عنصر في المكتبة"""
    import sqlite3
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT file_id, file_type, caption 
                 FROM library_files 
                 WHERE library_item_id = ?
                 ORDER BY file_order''',
              (library_item_id,))
    results = c.fetchall()
    conn.close()
    return results

def get_library_files_count(library_item_id):
    """الحصول على عدد ملفات عنصر في المكتبة"""
    import sqlite3
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) 
                 FROM library_files 
                 WHERE library_item_id = ?''',
              (library_item_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

# ============== 3. معالج رفع ملفات متعددة محسّن ==============

async def handle_multi_file_upload(update, context):
    """معالج محسّن لرفع ملفات متعددة"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    user = update.effective_user
    message = update.message
    
    # التحقق من وجود ملف
    file_id = None
    file_type = None
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    elif message.document:
        file_id = message.document.file_id
        file_type = 'document'
    
    if not file_id:
        return
    
    # إضافة الملف للقائمة المؤقتة
    if 'upload_files' not in context.user_data:
        context.user_data['upload_files'] = []
    
    context.user_data['upload_files'].append({
        'file_id': file_id,
        'file_type': file_type,
        'caption': message.caption or ""
    })
    
    files_count = len(context.user_data['upload_files'])
    
    # عرض رسالة تأكيد مع خيارات
    keyboard = [
        [InlineKeyboardButton(f"➕ رفع المزيد (حالياً: {files_count})", callback_data='upload_more')],
        [InlineKeyboardButton("✅ انتهيت من الرفع", callback_data='finish_multi_upload')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='cancel_multi_upload')]
    ]
    
    await message.reply_text(
        f"📎 **تم استلام الملف #{files_count}**\n\n"
        f"📊 الملفات المرفوعة: **{files_count}**\n\n"
        f"يمكنك رفع المزيد من الملفات أو الضغط على 'انتهيت' للمتابعة",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# ============== 4. معالج عرض تفاصيل الكتاب مع معرض الصور ==============

async def show_book_details_with_gallery(query, context, book_id):
    """عرض تفاصيل الكتاب مع معرض الصور"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.constants import ParseMode
    from database import get_library_item
    from advanced_features import get_book_details_text
    import sqlite3
    
    item = get_library_item(book_id)
    if not item:
        await query.edit_message_text("❌ لم يتم العثور على الكتاب.")
        return
    
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
    
    # عرض تفاصيل الكتاب
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
    from database import is_favorite, user_has_rated
    
    is_fav = is_favorite(query.from_user.id, book_id)
    has_rated = user_has_rated(book_id, query.from_user.id)
    
    if is_fav:
        keyboard.append([InlineKeyboardButton("⭐ إزالة من المفضلة", callback_data=f'unfav_{book_id}')])
    else:
        keyboard.append([InlineKeyboardButton("⭐ إضافة للمفضلة", callback_data=f'fav_{book_id}')])
    
    if not has_rated:
        keyboard.append([InlineKeyboardButton("⭐ قيّم هذا الكتاب", callback_data=f'rate_book_{book_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 الرجوع", callback_data='library_browse')])
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ============== 5. معالج عرض المعرض ==============

async def show_gallery_handler(query, context, book_id):
    """عرض معرض الصور بشكل جميل"""
    from telegram import InputMediaPhoto, InputMediaDocument
    
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

# ============== 6. معالج تحميل جميع الملفات ==============

async def download_all_files_handler(query, context, book_id):
    """تحميل جميع ملفات الكتاب"""
    files = get_library_files(book_id)
    
    if not files:
        await query.answer("⚠️ لا توجد ملفات للتحميل", show_alert=True)
        return
    
    await query.answer(f"📥 جاري إرسال {len(files)} ملف...")
    
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

# ============== 7. تحديث معالج الأزرار الرئيسي ==============

def update_button_handler_code():
    """
    الكود الذي يجب إضافته لمعالج الأزرار في main.py
    """
    code = '''
    # إضافة معالجات جديدة في button_handler
    
    # معالج عرض المعرض
    elif query.data.startswith('show_gallery_'):
        book_id = int(query.data.split('_')[2])
        await show_gallery_handler(query, context, book_id)
    
    # معالج تحميل جميع الملفات
    elif query.data.startswith('download_all_'):
        book_id = int(query.data.split('_')[2])
        await download_all_files_handler(query, context, book_id)
    
    # معالج إنهاء رفع ملفات متعددة
    elif query.data == 'finish_multi_upload':
        files_count = len(context.user_data.get('upload_files', []))
        if files_count == 0:
            await query.answer("⚠️ لم يتم رفع أي ملفات", show_alert=True)
            return
        
        await query.edit_message_text(
            f"📝 **اكتب عنواناً للملفات:**\\n\\n"
            f"📊 عدد الملفات: **{files_count}**\\n\\n"
            f"💡 مثال: ملخص الرياضيات - الفصل الثالث",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_library_title'] = True
    
    # معالج إضافة المزيد من الملفات
    elif query.data == 'upload_more':
        files_count = len(context.user_data.get('upload_files', []))
        await query.edit_message_text(
            f"📎 **أرسل الملف التالي**\\n\\n"
            f"📊 الملفات المرفوعة حالياً: **{files_count}**\\n\\n"
            f"يمكنك إرسال صور أو مستندات إضافية",
            parse_mode='Markdown'
        )
    
    # معالج إلغاء رفع متعدد
    elif query.data == 'cancel_multi_upload':
        context.user_data.pop('upload_files', None)
        await query.edit_message_text(
            "❌ **تم إلغاء عملية الرفع**\\n\\n"
            "📌 للرجوع: /start",
            parse_mode='Markdown'
        )
    '''
    return code

# ============== 8. الكود الكامل المحدث لعرض تفاصيل الكتاب ==============

UPDATED_VIEW_BOOK_HANDLER = '''
# استبدال معالج view_book_ في main.py بهذا الكود:

elif query.data.startswith('view_book_'):
    book_id = int(query.data.split('_')[2])
    await show_book_details_with_gallery(query, context, book_id)
'''

print("""
=========================================
تعليمات التطبيق:
=========================================

1. أولاً، قم بتشغيل الدالة لتحديث قاعدة البيانات:
   update_database_for_multi_files()

2. أضف الدوال الجديدة إلى ملف database.py:
   - add_library_file
   - get_library_files  
   - get_library_files_count

3. أضف معالجات الأزرار الجديدة في main.py:
   - show_gallery_
   - download_all_
   - finish_multi_upload
   - upload_more
   - cancel_multi_upload

4. حدث معالج رفع الملفات ليدعم الملفات المتعددة

5. حدث معالج view_book_ ليستخدم show_book_details_with_gallery

هذا سيوفر:
✅ رفع عدة ملفات لنفس الكتاب
✅ عرض جميع الصور كمعرض جميل
✅ تحميل جميع الملفات دفعة واحدة
✅ واجهة سهلة الاستخدام
""")