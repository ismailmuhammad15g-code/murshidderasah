import sqlite3
from datetime import datetime

def init_db():
    """تهيئة قاعدة البيانات وإنشاء الجداول"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    
    # جدول المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  name TEXT, 
                  email TEXT,
                  join_date TEXT,
                  notifications_enabled INTEGER DEFAULT 1)''')
    
    # جدول الأدمن
    c.execute('''CREATE TABLE IF NOT EXISTS admins
                 (user_id INTEGER PRIMARY KEY, is_admin INTEGER)''')
    
    # جدول حالة الكتب الدراسية
    c.execute('''CREATE TABLE IF NOT EXISTS books_status
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  message TEXT,
                  updated_at TEXT,
                  updated_by INTEGER)''')
    
    # جدول المكتبة (الكتب والمقالات والمنشورات)
    c.execute('''CREATE TABLE IF NOT EXISTS library
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  file_id TEXT,
                  file_type TEXT,
                  content_type TEXT DEFAULT 'book',
                  category TEXT DEFAULT 'عام',
                  uploader_id INTEGER,
                  uploader_name TEXT,
                  upload_date TEXT,
                  approved INTEGER DEFAULT 0,
                  approved_by INTEGER,
                  downloads INTEGER DEFAULT 0,
                  views INTEGER DEFAULT 0,
                  total_rating REAL DEFAULT 0,
                  rating_count INTEGER DEFAULT 0)''')

    # جدول ملفات العناصر المرتبطة (لمعرض الصور والملفات المتعددة)
    c.execute('''CREATE TABLE IF NOT EXISTS library_files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  library_item_id INTEGER,
                  file_id TEXT,
                  file_type TEXT,
                  file_order INTEGER DEFAULT 0,
                  caption TEXT,
                  local_path TEXT)''')
    
    # جدول التقييمات
    c.execute('''CREATE TABLE IF NOT EXISTS ratings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  book_id INTEGER,
                  user_id INTEGER,
                  rating INTEGER,
                  review TEXT,
                  created_at TEXT,
                  UNIQUE(book_id, user_id))''')
    
    # جدول المفضلة
    c.execute('''CREATE TABLE IF NOT EXISTS favorites
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  book_id INTEGER,
                  added_at TEXT,
                  UNIQUE(user_id, book_id))''')
    
    # جدول الإشعارات
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  title TEXT,
                  message TEXT,
                  created_at TEXT,
                  read INTEGER DEFAULT 0,
                  notification_type TEXT)''')
    
    # جدول التذكيرات
    c.execute('''CREATE TABLE IF NOT EXISTS reminders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  description TEXT,
                  reminder_date TEXT,
                  created_by INTEGER,
                  created_at TEXT,
                  active INTEGER DEFAULT 1,
                  sent INTEGER DEFAULT 0)''')
    
    # جدول الأخبار (بديل أفضل من الأخبار الثابتة)
    c.execute('''CREATE TABLE IF NOT EXISTS news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  content TEXT,
                  created_by INTEGER,
                  created_at TEXT,
                  active INTEGER DEFAULT 1,
                  priority INTEGER DEFAULT 0)''')
    
    # جدول الإعلانات للمستخدمين الجدد
    c.execute('''CREATE TABLE IF NOT EXISTS ads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  message TEXT,
                  image_file_id TEXT,
                  is_active INTEGER DEFAULT 1,
                  created_at TEXT,
                  created_by INTEGER)''')

    # جدول حالة توفر الكتب بحسب الصف والمادة
    c.execute('''CREATE TABLE IF NOT EXISTS books_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    grade TEXT,
                    subject TEXT,
                    status TEXT,           -- available | partial | unavailable
                    eta TEXT,              -- تاريخ متوقع اختياري
                    note TEXT,
                    updated_at TEXT,
                    updated_by INTEGER
                )''')
    
    # Migration: Add views column if it doesn't exist
    try:
        c.execute("SELECT views FROM library LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE library ADD COLUMN views INTEGER DEFAULT 0")
    
    # Migration: Add total_rating column if it doesn't exist
    try:
        c.execute("SELECT total_rating FROM library LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE library ADD COLUMN total_rating REAL DEFAULT 0")
    
    # Migration: Add rating_count column if it doesn't exist
    try:
        c.execute("SELECT rating_count FROM library LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE library ADD COLUMN rating_count INTEGER DEFAULT 0")
    
    # Migration: Add content_type column if it doesn't exist
    try:
        c.execute("SELECT content_type FROM library LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE library ADD COLUMN content_type TEXT DEFAULT 'book'")
    
    # Migration: Add local_path to library_files if it doesn't exist
    try:
        c.execute("SELECT local_path FROM library_files LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE library_files ADD COLUMN local_path TEXT")
        except sqlite3.OperationalError:
            pass
    
    # Migration: Add join_date to users if it doesn't exist
    try:
        c.execute("SELECT join_date FROM users LIMIT 1")
    except sqlite3.OperationalError:
        try:
            c.execute("ALTER TABLE users ADD COLUMN join_date TEXT")
            print("✅ تم إضافة عمود join_date لجدول users")
        except sqlite3.OperationalError as e:
            print(f"⚠️ خطأ في إضافة join_date: {e}")

    # Index لتحسين الاستعلامات
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_books_inventory_grade_subject ON books_inventory(grade, subject)")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def add_user(user_id, name):
    """إضافة مستخدم جديد إلى قاعدة البيانات"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()

def is_admin(user_id):
    """التحقق من صلاحيات الأدمن للمستخدم"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT is_admin FROM admins WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def add_admin(user_id):
    """إضافة أدمن جديد"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO admins (user_id, is_admin) VALUES (?, 1)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    """الحصول على جميع معرفات المستخدمين"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_all_admins():
    """الحصول على جميع معرفات الأدمن"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins")
    admins = [row[0] for row in c.fetchall()]
    conn.close()
    return admins

# ========== وظائف حالة الكتب ==========

def set_books_status(message, admin_id):
    """تحديث حالة الكتب"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("DELETE FROM books_status")
    c.execute("INSERT INTO books_status (message, updated_at, updated_by) VALUES (?, ?, ?)",
              (message, now, admin_id))
    conn.commit()
    conn.close()

def get_books_status():
    """الحصول على آخر حالة للكتب"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT message, updated_at FROM books_status ORDER BY id DESC LIMIT 1")
    result = c.fetchone()
    conn.close()
    if result:
        return {"message": result[0], "updated_at": result[1]}
    return None

# ========== وظائف المكتبة ==========

def add_to_library(title, description, file_id, file_type, category, uploader_id, uploader_name, approved=0, content_type='book'):
    """إضافة كتاب/صورة/مقال/منشور للمكتبة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO library (title, description, file_id, file_type, category, 
                 uploader_id, uploader_name, upload_date, approved, content_type)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (title, description, file_id, file_type, category, uploader_id, uploader_name, now, approved, content_type))
    conn.commit()
    item_id = c.lastrowid
    conn.close()
    return item_id

def get_library_stats():
    """الحصول على إحصائيات المكتبة مع التصنيف حسب النوع"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    
    # إحصائيات عامة
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 1")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 0")
    pending = c.fetchone()[0]
    
    # إحصائيات حسب نوع المحتوى
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 1 AND content_type = 'book'")
    books = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 1 AND content_type = 'image'")
    images = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 1 AND content_type = 'article'")
    articles = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 1 AND content_type = 'post'")
    posts = c.fetchone()[0]
    
    conn.close()
    return {
        "total": total, 
        "pending": pending,
        "books": books,
        "images": images,
        "articles": articles,
        "posts": posts
    }

def search_library(keyword):
    """البحث في المكتبة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, description, file_id, uploader_name, downloads 
                 FROM library WHERE approved = 1 AND (title LIKE ? OR description LIKE ?)
                 ORDER BY downloads DESC LIMIT 10''',
              (f'%{keyword}%', f'%{keyword}%'))
    results = c.fetchall()
    conn.close()
    return results

def get_library_item(item_id):
    """الحصول على معلومات عنصر من المكتبة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM library WHERE id = ?", (item_id,))
    result = c.fetchone()
    conn.close()
    return result

def increment_downloads(item_id):
    """زيادة عداد التحميلات"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("UPDATE library SET downloads = downloads + 1 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def approve_library_item(item_id, admin_id):
    """الموافقة على عنصر في المكتبة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("UPDATE library SET approved = 1, approved_by = ? WHERE id = ?", (admin_id, item_id))
    conn.commit()
    conn.close()

def delete_library_item(item_id):
    """حذف عنصر من المكتبة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM library WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

def get_pending_library_items():
    """الحصول على العناصر بانتظار الموافقة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, uploader_name, upload_date 
                 FROM library WHERE approved = 0 ORDER BY upload_date DESC''')
    results = c.fetchall()
    conn.close()
    return results

def get_all_library_items():
    """الحصول على جميع عناصر المكتبة المعتمدة (قديمة - للإبقاء على التوافق)"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, description, uploader_name, downloads 
                 FROM library WHERE approved = 1 ORDER BY downloads DESC LIMIT 20''')
    results = c.fetchall()
    conn.close()
    return results

def count_library_items(content_type=None):
    """عدد عناصر المكتبة (حسب النوع اختياري)"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    if content_type and content_type != 'all':
        c.execute("SELECT COUNT(*) FROM library WHERE approved = 1 AND content_type = ?", (content_type,))
    else:
        c.execute("SELECT COUNT(*) FROM library WHERE approved = 1")
    total = c.fetchone()[0]
    conn.close()
    return total

def get_library_items_paginated(content_type=None, page=1, page_size=8):
    """جلب عناصر المكتبة بترقيم صفحات مع نوع محتوى اختياري"""
    offset = (page - 1) * page_size
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    if content_type and content_type != 'all':
        c.execute('''SELECT id, title, uploader_name, downloads, content_type, category, upload_date
                     FROM library
                     WHERE approved = 1 AND content_type = ?
                     ORDER BY upload_date DESC
                     LIMIT ? OFFSET ?''', (content_type, page_size, offset))
    else:
        c.execute('''SELECT id, title, uploader_name, downloads, content_type, category, upload_date
                     FROM library
                     WHERE approved = 1
                     ORDER BY upload_date DESC
                     LIMIT ? OFFSET ?''', (page_size, offset))
    results = c.fetchall()
    conn.close()
    return results

def get_user_library_items(user_id):
    """الحصول على كتب مستخدم معين"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, description, approved, upload_date, downloads 
                 FROM library WHERE uploader_id = ? ORDER BY upload_date DESC''',
              (user_id,))
    results = c.fetchall()
    conn.close()
    return results

# ========== وظائف التقييمات ==========

def add_rating(book_id, user_id, rating, review=""):
    """إضافة تقييم لكتاب"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        c.execute('''INSERT INTO ratings (book_id, user_id, rating, review, created_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (book_id, user_id, rating, review, now))
        
        # تحديث متوسط التقييم
        c.execute('''UPDATE library 
                     SET total_rating = total_rating + ?, 
                         rating_count = rating_count + 1
                     WHERE id = ?''', (rating, book_id))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        # المستخدم قيّم الكتاب مسبقاً
        success = False
    conn.close()
    return success

def get_book_rating(book_id):
    """الحصول على متوسط تقييم كتاب"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT total_rating, rating_count FROM library WHERE id = ?''', (book_id,))
    result = c.fetchone()
    conn.close()
    if result and result[1] > 0:
        return result[0] / result[1], result[1]
    return 0, 0

def get_book_reviews(book_id, limit=5):
    """الحصول على مراجعات كتاب"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT r.rating, r.review, r.created_at, u.name
                 FROM ratings r
                 JOIN users u ON r.user_id = u.user_id
                 WHERE r.book_id = ? AND r.review != ""
                 ORDER BY r.created_at DESC LIMIT ?''',
              (book_id, limit))
    results = c.fetchall()
    conn.close()
    return results

def user_has_rated(book_id, user_id):
    """التحقق من إذا قيّم المستخدم الكتاب"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id FROM ratings WHERE book_id = ? AND user_id = ?''',
              (book_id, user_id))
    result = c.fetchone()
    conn.close()
    return result is not None

# ========== وظائف المفضلة ==========

def add_to_favorites(user_id, book_id):
    """إضافة كتاب للمفضلة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        c.execute('''INSERT INTO favorites (user_id, book_id, added_at)
                     VALUES (?, ?, ?)''', (user_id, book_id, now))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def remove_from_favorites(user_id, book_id):
    """إزالة كتاب من المفضلة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''DELETE FROM favorites WHERE user_id = ? AND book_id = ?''',
              (user_id, book_id))
    conn.commit()
    conn.close()

def is_favorite(user_id, book_id):
    """التحقق من إذا كان الكتاب في المفضلة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id FROM favorites WHERE user_id = ? AND book_id = ?''',
              (user_id, book_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_user_favorites(user_id):
    """الحصول على كتب المفضلة للمستخدم"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT l.id, l.title, l.category, l.downloads, 
                        l.total_rating, l.rating_count
                 FROM favorites f
                 JOIN library l ON f.book_id = l.id
                 WHERE f.user_id = ? AND l.approved = 1
                 ORDER BY f.added_at DESC''',
              (user_id,))
    results = c.fetchall()
    conn.close()
    return results

# ========== وظائف الإشعارات ==========

def add_notification(user_id, title, message, notification_type):
    """إضافة إشعار للمستخدم"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO notifications (user_id, title, message, created_at, notification_type)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, title, message, now, notification_type))
    conn.commit()
    conn.close()

def get_user_notifications(user_id, unread_only=False):
    """الحصول على إشعارات المستخدم"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    if unread_only:
        c.execute('''SELECT id, title, message, created_at, notification_type
                     FROM notifications
                     WHERE user_id = ? AND read = 0
                     ORDER BY created_at DESC LIMIT 10''', (user_id,))
    else:
        c.execute('''SELECT id, title, message, created_at, notification_type
                     FROM notifications
                     WHERE user_id = ?
                     ORDER BY created_at DESC LIMIT 20''', (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def mark_notification_read(notification_id):
    """وضع علامة مقروء على إشعار"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''UPDATE notifications SET read = 1 WHERE id = ?''', (notification_id,))
    conn.commit()
    conn.close()

def get_unread_count(user_id):
    """عدد الإشعارات غير المقروءة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read = 0''',
              (user_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

# ========== وظائف التذكيرات ==========

def add_reminder(title, description, reminder_date, admin_id):
    """إضافة تذكير"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO reminders (title, description, reminder_date, created_by, created_at)
                 VALUES (?, ?, ?, ?, ?)''',
              (title, description, reminder_date, admin_id, now))
    conn.commit()
    reminder_id = c.lastrowid
    conn.close()
    return reminder_id

def get_active_reminders():
    """الحصول على التذكيرات النشطة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, description, reminder_date
                 FROM reminders
                 WHERE active = 1 AND sent = 0
                 ORDER BY reminder_date ASC''')  
    results = c.fetchall()
    conn.close()
    return results

def mark_reminder_sent(reminder_id):
    """وضع علامة مُرسل على تذكير"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''UPDATE reminders SET sent = 1 WHERE id = ?''', (reminder_id,))
    conn.commit()
    conn.close()

# ========== وظائف الأخبار ==========

def add_news(title, content, admin_id, priority=0):
    """إضافة خبر جديد"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO news (title, content, created_by, created_at, priority)
                 VALUES (?, ?, ?, ?, ?)''',
              (title, content, admin_id, now, priority))
    conn.commit()
    news_id = c.lastrowid
    conn.close()
    return news_id

def get_active_news(limit=10):
    """الحصول على الأخبار النشطة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, content, created_at
                 FROM news
                 WHERE active = 1
                 ORDER BY priority DESC, created_at DESC
                 LIMIT ?''', (limit,))
    results = c.fetchall()
    conn.close()
    return results

def delete_news(news_id):
    """حذف خبر"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''UPDATE news SET active = 0 WHERE id = ?''', (news_id,))
    conn.commit()
    conn.close()

# ========== وظائف محسّنة للمكتبة ==========

def get_library_by_category(category):
    """الحصول على كتب حسب الفئة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, downloads, total_rating, rating_count
                 FROM library 
                 WHERE approved = 1 AND category = ?
                 ORDER BY downloads DESC
                 LIMIT 20''', (category,))
    results = c.fetchall()
    conn.close()
    return results

def get_categories():
    """الحصول على جميع الفئات"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT DISTINCT category, COUNT(*) as count
                 FROM library
                 WHERE approved = 1
                 GROUP BY category
                 ORDER BY count DESC''')
    results = c.fetchall()
    conn.close()
    return results

def increment_views(book_id):
    """زيادة عداد المشاهدات"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("UPDATE library SET views = views + 1 WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()

def get_popular_books(limit=10):
    """الحصول على الكتب الأكثر شعبية"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, category, downloads, views, total_rating, rating_count
                 FROM library
                 WHERE approved = 1
                 ORDER BY downloads DESC, views DESC
                 LIMIT ?''', (limit,))
    results = c.fetchall()
    conn.close()
    return results

def get_top_rated_books(limit=10):
    """الحصول على الكتب الأعلى تقييماً"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, category, total_rating, rating_count, downloads
                 FROM library
                 WHERE approved = 1 AND rating_count > 0
                 ORDER BY (total_rating * 1.0 / rating_count) DESC
                 LIMIT ?''', (limit,))
    results = c.fetchall()
    conn.close()
    return results

# ========== وظائف الملفات المتعددة ==========

def add_library_file(library_item_id, file_id, file_type, file_order=0, caption="", local_path=None):
    """إضافة ملف لعنصر في المكتبة"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO library_files (library_item_id, file_id, file_type, file_order, caption, local_path)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (library_item_id, file_id, file_type, file_order, caption, local_path))
    except sqlite3.OperationalError:
        # في حال لم يكن عمود local_path موجوداً لأي سبب
        c.execute('''INSERT INTO library_files (library_item_id, file_id, file_type, file_order, caption)
                     VALUES (?, ?, ?, ?, ?)''',
                  (library_item_id, file_id, file_type, file_order, caption))
    conn.commit()
    conn.close()

def get_library_files(library_item_id):
    """الحصول على جميع ملفات عنصر في المكتبة"""
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
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT COUNT(*) 
                 FROM library_files 
                 WHERE library_item_id = ?''',
              (library_item_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_admin_stats():
    """إحصائيات شاملة للأدمن"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    
    stats = {}
    
    # عدد المستخدمين
    c.execute("SELECT COUNT(*) FROM users")
    stats['total_users'] = c.fetchone()[0]
    
    # عدد الكتب
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 1")
    stats['approved_books'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM library WHERE approved = 0")
    stats['pending_books'] = c.fetchone()[0]
    
    # إجمالي التحميلات
    c.execute("SELECT SUM(downloads) FROM library")
    result = c.fetchone()[0]
    stats['total_downloads'] = result if result else 0
    
    # عدد التقييمات
    c.execute("SELECT COUNT(*) FROM ratings")
    stats['total_ratings'] = c.fetchone()[0]
    
    # عدد الإشعارات غير المقروءة
    c.execute("SELECT COUNT(*) FROM notifications WHERE read = 0")
    stats['unread_notifications'] = c.fetchone()[0]
    
    conn.close()
    return stats

# ========== وظائف حالة الكتب المتقدمة ==========

def upsert_book_inventory(grade, subject, status, eta, note, admin_id):
    """إضافة/تحديث حالة مادة لصف معين"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("SELECT id FROM books_inventory WHERE grade = ? AND subject = ?", (grade, subject))
    row = c.fetchone()
    if row:
        c.execute('''UPDATE books_inventory
                     SET status = ?, eta = ?, note = ?, updated_at = ?, updated_by = ?
                     WHERE id = ?''', (status, eta, note, now, admin_id, row[0]))
        item_id = row[0]
    else:
        c.execute('''INSERT INTO books_inventory (grade, subject, status, eta, note, updated_at, updated_by)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', (grade, subject, status, eta, note, now, admin_id))
        item_id = c.lastrowid
    conn.commit()
    conn.close()
    return item_id

def get_books_inventory_summary():
    """ملخص حسب الحالة وعدد العناصر"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT status, COUNT(*) FROM books_inventory GROUP BY status")
    rows = c.fetchall()
    c.execute("SELECT COUNT(*) FROM books_inventory")
    total = c.fetchone()[0]
    conn.close()
    summary = {r[0]: r[1] for r in rows}
    summary['total'] = total
    return summary

def get_grades():
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT grade FROM books_inventory ORDER BY grade")
    grades = [r[0] for r in c.fetchall()]
    conn.close()
    return grades

def get_subjects_by_grade(grade):
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT subject FROM books_inventory WHERE grade = ? ORDER BY subject", (grade,))
    subjects = [r[0] for r in c.fetchall()]
    conn.close()
    return subjects

def get_books_by_grade(grade):
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT subject, status, eta, note, updated_at
                 FROM books_inventory
                 WHERE grade = ?
                 ORDER BY subject''', (grade,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_recent_books_updates(limit=5):
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT grade, subject, status, eta, updated_at
                 FROM books_inventory
                 ORDER BY updated_at DESC
                 LIMIT ?''', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_user_notifications_enabled(user_id):
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT notifications_enabled FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else True

def set_user_notifications_enabled(user_id, enabled):
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("UPDATE users SET notifications_enabled = ? WHERE user_id = ?", (1 if enabled else 0, user_id))
    conn.commit()
    conn.close()

def get_all_users_notifications_enabled():
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE notifications_enabled = 1")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

# ========== دوال إدارة الإعلانات ==========

def get_active_ad():
    """الحصول على الإعلان النشط الحالي"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, message, image_file_id, created_at
                 FROM ads 
                 WHERE is_active = 1
                 ORDER BY created_at DESC
                 LIMIT 1''')
    result = c.fetchone()
    conn.close()
    return result

def get_all_ads():
    """الحصول على جميع الإعلانات"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute('''SELECT id, title, message, image_file_id, is_active, created_at
                 FROM ads 
                 ORDER BY created_at DESC''')
    results = c.fetchall()
    conn.close()
    return results

def add_ad(title, message, image_file_id, admin_id):
    """إضافة إعلان جديد"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''INSERT INTO ads (title, message, image_file_id, is_active, created_at, created_by)
                 VALUES (?, ?, ?, 1, ?, ?)''', (title, message, image_file_id, now, admin_id))
    ad_id = c.lastrowid
    conn.commit()
    conn.close()
    return ad_id

def delete_ad(ad_id):
    """حذف إعلان"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM ads WHERE id = ?", (ad_id,))
    conn.commit()
    conn.close()

def toggle_ad_status(ad_id, is_active):
    """تفعيل/إيقاف إعلان"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("UPDATE ads SET is_active = ? WHERE id = ?", (1 if is_active else 0, ad_id))
    conn.commit()
    conn.close()

def is_new_user(user_id):
    """التحقق إذا كان المستخدم جديد"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    c.execute("SELECT join_date FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    # إذا لم يوجد join_date أو كان NULL فهو مستخدم جديد
    return result is None or result[0] is None

def mark_user_joined(user_id):
    """تسجيل تاريخ انضمام المستخدم"""
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute("UPDATE users SET join_date = ? WHERE user_id = ? AND join_date IS NULL", (now, user_id))
    conn.commit()
    conn.close()
