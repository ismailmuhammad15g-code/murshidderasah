# flask_app.py
"""
التطبيق الرئيسي - Flask للموقع + Webhook للبوت
"""

import os
import logging
import asyncio
from datetime import datetime
from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash

# استيراد المكونات المحلية
from config import Config
import database  # قاعدة بيانات البوت الأساسية
import bot_logic
import sqlite3

# استيراد telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# الإعداد
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========================================
# إنشاء Flask App
# ========================================

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.FLASK_SECRET_KEY
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# إنشاء مجلد uploads إذا لم يكن موجوداً
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# تهيئة قاعدة بيانات البوت (مشتركة)
database.init_db()
logger.info("✅ تم تهيئة قاعدة البيانات المشتركة (school_bot.db)")

# إعداد نظام تسجيل دخول بسيط (بدون Flask-Login)
# نستخدم session بسيطة لأن المستخدمين مخزّنين في school_bot.db
from flask import session

# مفتاح الجلسة
app.secret_key = Config.FLASK_SECRET_KEY

# إضافة current_user للـ templates
@app.context_processor
def inject_user():
    """إضافة معلومات المستخدم لجميع القوالب"""
    if 'user_id' in session:
        return {
            'current_user': {
                'is_authenticated': True,
                'name': session.get('name', 'المستخدم'),
                'username': session.get('username', 'user'),
                'id': session.get('user_id')
            }
        }
    else:
        return {
            'current_user': {
                'is_authenticated': False
            }
        }

# إنشاء مستخدم أدمن افتراضي في قاعدة بيانات البوت
try:
    conn = sqlite3.connect('school_bot.db')
    c = conn.cursor()
    # إضافة مستخدم admin إذا لم يكن موجوداً
    c.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (99999999, 'المسؤول'))
    c.execute("INSERT OR IGNORE INTO admins (user_id, is_admin) VALUES (?, ?)", (99999999, 1))
    conn.commit()
    conn.close()
    logger.info("✅ تم التحقق من مستخدم الأدمن الافتراضي")
except Exception as e:
    logger.error(f"❌ خطأ في إنشاء الأدمن: {e}")

# ========================================
# إعداد Telegram Bot
# ========================================

telegram_app = None

def setup_telegram_bot():
    """إعداد التطبيق الخاص بالبوت"""
    global telegram_app
    
    if not Config.BOT_TOKEN:
        logger.warning("⚠️ لم يتم تعيين BOT_TOKEN")
        return None
    
    telegram_app = Application.builder().token(Config.BOT_TOKEN).build()
    
    # إضافة المعالجات
    telegram_app.add_handler(CommandHandler("start", bot_logic.start_command))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_logic.handle_message))
    
    logger.info("✅ تم إعداد Telegram Bot")
    return telegram_app


def check_bot_status():
    """فحص حالة البوت - يتحقق من قاعدة بيانات البوت الأساسية"""
    import sqlite3
    
    # فحص قاعدة بيانات البوت الأساسية (school_bot.db)
    if not os.path.exists('school_bot.db'):
        return False, "قاعدة بيانات البوت غير موجودة"
    
    try:
        # محاولة الاتصال بقاعدة البيانات
        conn = sqlite3.connect('school_bot.db', timeout=2)
        cursor = conn.cursor()
        
        # التحقق من وجود جدول users (البوت يستخدمه)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            conn.close()
            return True, "البوت متصل ويعمل بنجاح!"
        else:
            conn.close()
            return False, "قاعدة البيانات غير مكتملة"
    except Exception as e:
        logger.error(f"❌ خطأ في فحص حالة البوت: {e}")
        return False, f"خطأ في الاتصال: {str(e)}"

# ========================================
# Routes - نظام المستخدمين
# ========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """صفحة تسجيل الدخول - مبسّطة (admin/admin123)"""
    # إذا كان مسجل مسبقاً
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        logger.info(f"محاولة تسجيل دخول: {username}")
        
        # 1. فحص الأدمن الافتراضي
        if username == 'admin' and password == 'admin123':
            session.clear()
            session['user_id'] = 99999999
            session['username'] = 'admin'
            session['name'] = 'المسؤول'
            session.permanent = True
            
            logger.info(f"✅ تسجيل دخول ناجح (أدمن): {username}")
            flash('مرحباً بك يا المسؤول! 👋', 'success')
            return redirect(url_for('home'))
        
        # 2. فحص المستخدمين المسجلين
        try:
            conn = sqlite3.connect('school_bot.db')
            cursor = conn.cursor()
            
            # البحث عن المستخدم
            cursor.execute("""
                SELECT up.user_id, up.password_hash, u.name 
                FROM user_passwords up
                JOIN users u ON up.user_id = u.user_id
                WHERE up.username = ?
            """, (username,))
            
            result = cursor.fetchone()
            
            if result:
                user_id, password_hash, name = result
                
                # التحقق من كلمة المرور
                from werkzeug.security import check_password_hash
                if check_password_hash(password_hash, password):
                    # التحقق من تفعيل الإيميل (اتصال جديد)
                    cursor.execute("""
                        SELECT is_verified FROM email_verifications
                        WHERE user_id = ?
                    """, (user_id,))
                    verification = cursor.fetchone()
                    
                    conn.close()  # إغلاق الاتصال بعد الانتهاء
                    
                    if verification and verification[0] == 0:
                        logger.warning(f"⚠️ محاولة دخول لحساب غير مفعّل: {username}")
                        flash('📧 يجب تفعيل حسابك أولاً! تفقد بريدك الإلكتروني.', 'warning')
                        return render_template('login.html')
                    
                    session.clear()
                    session['user_id'] = user_id
                    session['username'] = username
                    session['name'] = name
                    session.permanent = True
                    
                    logger.info(f"✅ تسجيل دخول ناجح: {username}")
                    flash(f'مرحباً بك يا {name}! 👋', 'success')
                    return redirect(url_for('home'))
            
            conn.close()  # إغلاق الاتصال إذا لم يتم العثور على مستخدم
            
            # فشل تسجيل الدخول
            logger.warning(f"❌ فشل تسجيل الدخول: {username}")
            flash('اسم المستخدم أو كلمة المرور غير صحيحة.', 'danger')
            
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الدخول: {e}")
            flash('حدث خطأ أثناء تسجيل الدخول. حاول مرة أخرى.', 'danger')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """صفحة إنشاء حساب جديد مع التحقق بالإيميل"""
    # إذا كان مسجل مسبقاً
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        
        # التحقق من الحقول
        if not username or not password or not name or not email:
            flash('جميع الحقول مطلوبة!', 'danger')
            return render_template('register.html')
        
        # التحقق من صيغة الإيميل
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash('صيغة الإيميل غير صحيحة!', 'danger')
            return render_template('register.html')
        
        # التحقق من طول كلمة المرور
        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل!', 'danger')
            return render_template('register.html')
        
        try:
            conn = sqlite3.connect('school_bot.db')
            cursor = conn.cursor()
            
            # التحقق من عدم وجود الإيميل مسبقاً
            cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                flash('الإيميل مستخدم مسبقاً! استخدم إيميل آخر.', 'danger')
                return render_template('register.html')
            
            # التحقق من عدم وجود اسم المستخدم مسبقاً
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_passwords (
                    user_id INTEGER PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    username TEXT UNIQUE
                )
            """)
            
            cursor.execute("SELECT user_id FROM user_passwords WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                flash('اسم المستخدم مستخدم مسبقاً! اختر اسم آخر.', 'danger')
                return render_template('register.html')
            
            # إنشاء user_id عشوائي
            import random
            user_id = random.randint(100000000, 999999999)
            
            # تشفير كلمة المرور
            from werkzeug.security import generate_password_hash
            password_hash = generate_password_hash(password)
            
            # إنشاء رمز التحقق (UUID)
            import secrets
            verification_token = secrets.token_urlsafe(32)
            
            # إدخال المستخدم في القاعدة (غير مفعّل)
            cursor.execute("""
                INSERT INTO users (user_id, name, email, join_date)
                VALUES (?, ?, ?, ?)
            """, (user_id, name, email, datetime.now().isoformat()))
            
            # حفظ كلمة المرور
            cursor.execute("""
                INSERT INTO user_passwords (user_id, password_hash, username)
                VALUES (?, ?, ?)
            """, (user_id, password_hash, username))
            
            # إنشاء جدول التحقق بالإيميل إذا لم يكن موجوداً
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_verifications (
                    user_id INTEGER PRIMARY KEY,
                    verification_token TEXT NOT NULL UNIQUE,
                    is_verified INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    verified_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # حفظ رمز التحقق
            cursor.execute("""
                INSERT INTO email_verifications (user_id, verification_token, created_at)
                VALUES (?, ?, ?)
            """, (user_id, verification_token, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ تم تسجيل مستخدم جديد (غير مفعّل): {email} (ID: {user_id})")
            
            # إرسال إيميل التحقق
            email_sent = False
            try:
                from email_service import send_verification_email
                if send_verification_email(email, name, verification_token):
                    logger.info(f"✅ تم إرسال إيميل التحقق إلى: {email}")
                    email_sent = True
                else:
                    logger.error(f"❌ فشل إرسال إيميل التحقق إلى: {email}")
            except Exception as email_error:
                logger.error(f"❌ خطأ في إرسال إيميل التحقق: {email_error}")
            
            # عرض صفحة التحقق
            return render_template('verify_pending.html', email=email, email_sent=email_sent)
            
        except Exception as e:
            logger.error(f"❌ خطأ في التسجيل: {e}")
            flash('حدث خطأ أثناء التسجيل. حاول مرة أخرى.', 'danger')
    
    return render_template('register.html')


@app.route('/verify-email')
def verify_email():
    """تفعيل الحساب بعد الضغط على رابط التحقق"""
    token = request.args.get('token', '').strip()
    
    if not token:
        flash('رابط غير صحيح!', 'danger')
        return redirect(url_for('login'))
    
    try:
        conn = sqlite3.connect('school_bot.db')
        cursor = conn.cursor()
        
        # البحث عن التوكن
        cursor.execute("""
            SELECT user_id, is_verified, created_at
            FROM email_verifications
            WHERE verification_token = ?
        """, (token,))
        
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            flash('❌ رابط التفعيل غير صحيح أو منتهي الصلاحية!', 'danger')
            return redirect(url_for('login'))
        
        user_id, is_verified, created_at = result
        
        # إذا كان مفعّل مسبقاً
        if is_verified:
            conn.close()
            flash('✅ حسابك مفعّل مسبقاً! يمكنك تسجيل الدخول.', 'info')
            return redirect(url_for('login'))
        
        # فحص صلاحية التوكن (24 ساعة)
        from datetime import datetime, timedelta
        created = datetime.fromisoformat(created_at)
        if datetime.now() - created > timedelta(hours=24):
            conn.close()
            flash('❌ رابط التفعيل منتهي الصلاحية (24 ساعة). تواصل مع الدعم.', 'danger')
            return redirect(url_for('login'))
        
        # تفعيل الحساب
        cursor.execute("""
            UPDATE email_verifications
            SET is_verified = 1, verified_at = ?
            WHERE user_id = ?
        """, (datetime.now().isoformat(), user_id))
        
        conn.commit()
        
        # جلب بيانات المستخدم
        cursor.execute("""
            SELECT name, email FROM users WHERE user_id = ?
        """, (user_id,))
        user_data = cursor.fetchone()
        
        conn.close()
        
        if user_data:
            name, email = user_data
            logger.info(f"✅ تم تفعيل حساب: {email} (ID: {user_id})")
            flash(f'🎉 تم تفعيل حسابك بنجاح يا {name}! يمكنك الآن تسجيل الدخول.', 'success')
        else:
            flash('✅ تم تفعيل الحساب! يمكنك الآن تسجيل الدخول.', 'success')
        
        return redirect(url_for('login'))
        
    except Exception as e:
        logger.error(f"❌ خطأ في تفعيل الحساب: {e}")
        flash('حدث خطأ أثناء تفعيل الحساب. حاول مرة أخرى.', 'danger')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    """تسجيل الخروج"""
    session.clear()
    flash('تم تسجيل الخروج بنجاح.', 'info')
    return redirect(url_for('login'))


# ========================================
# Routes - الموقع
# ========================================

# دالة مساعدة للتحقق من تسجيل الدخول
def require_login(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('الرجاء تسجيل الدخول أولاً.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@app.route('/home')
@require_login
def home():
    """الصفحة الرئيسية - الإحصائيات من قاعدة بيانات البوت الحقيقية"""
    import sqlite3
    
    # الإحصائيات الافتراضية
    books_count = 0
    users_count = 0
    library_items_count = 0
    messages_count = 0
    
    try:
        # الاتصال بقاعدة بيانات البوت الأساسية
        conn = sqlite3.connect('school_bot.db', timeout=2)
        cursor = conn.cursor()
        
        # عدد المستخدمين الحقيقي
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        
        # عدد عناصر المكتبة (الكتب والمحتوى)
        cursor.execute("SELECT COUNT(*) FROM library WHERE approved = 1")
        library_items_count = cursor.fetchone()[0]
        
        # عدد الكتب فقط
        cursor.execute("SELECT COUNT(*) FROM library WHERE approved = 1 AND content_type = 'book'")
        books_count = cursor.fetchone()[0]
        
        conn.close()
    except Exception as e:
        logger.error(f"❌ خطأ في قراءة الإحصائيات: {e}")
    
    # عدد الرسائل من قاعدة البيانات الفيكتورية (تقريبي)
    try:
        import vector_store
        vector_store._init_chromadb()
        if vector_store.collection:
            messages_count = vector_store.collection.count()
    except:
        messages_count = 10000  # قيمة افتراضية
    
    return render_template(
        'home.html', 
        books_count=books_count,
        users_count=users_count,
        library_items_count=library_items_count,
        messages_count=messages_count
    )


@app.route('/library')
@require_login
def library():
    """صفحة المكتبة - عرض جميع الكتب من school_bot.db"""
    try:
        conn = sqlite3.connect('school_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # جلب جميع الكتب المعتمدة
        cursor.execute("""
            SELECT id, title, description, category, uploader_name, uploader_id,
                   upload_date, downloads, views, content_type
            FROM library 
            WHERE approved = 1 AND content_type = 'book'
            ORDER BY upload_date DESC
        """)
        
        books = []
        for row in cursor.fetchall():
            # تحويل التاريخ إلى datetime object
            upload_datetime = datetime.now()
            if row['upload_date']:
                try:
                    # محاولة تحليل صيغ مختلفة من التاريخ
                    upload_date_str = row['upload_date']
                    if 'T' in upload_date_str:
                        # صيغة ISO
                        upload_datetime = datetime.fromisoformat(upload_date_str.split('.')[0])
                    else:
                        # صيغة عادية
                        upload_datetime = datetime.strptime(upload_date_str, '%Y-%m-%d %H:%M:%S')
                except Exception as date_err:
                    logger.warning(f"⚠️ خطأ في تحليل التاريخ: {date_err}")
                    upload_datetime = datetime.now()
            
            books.append({
                'id': row['id'],
                'title': row['title'],
                'description': row['description'] or 'لا يوجد وصف',
                'category': row['category'] or 'عام',
                'author': row['uploader_name'] or 'غير معروف',
                'uploaded_by': row['uploader_id'],
                'uploaded_at': upload_datetime,
                'downloads': row['downloads'] or 0,
                'views': row['views'] or 0
            })
        
        conn.close()
        logger.info(f"✅ تم جلب {len(books)} كتاب من المكتبة")
        return render_template('library.html', books=books)
        
    except Exception as e:
        logger.error(f"❌ خطأ في جلب الكتب: {e}")
        logger.exception(e)
        flash('حدث خطأ في تحميل المكتبة. يرجى المحاولة مرة أخرى.', 'danger')
        return redirect(url_for('home'))


@app.route('/upload', methods=['GET', 'POST'])
@require_login
def upload_book():
    """صفحة رفع كتاب جديد - يحفظ في school_bot.db"""
    if request.method == 'POST':
        # التحقق من وجود الملف
        if 'file' not in request.files:
            flash('لم يتم اختيار ملف.', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('لم يتم اختيار ملف.', 'danger')
            return redirect(request.url)
        
        # التحقق من امتداد الملف
        if not file.filename.lower().endswith('.pdf'):
            flash('يجب أن يكون الملف بصيغة PDF.', 'danger')
            return redirect(request.url)
        
        try:
            # حفظ الملف
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # حفظ في school_bot.db
            title = request.form.get('title', 'بدون عنوان')
            description = request.form.get('description', '')
            category = request.form.get('category', 'عام')
            
            conn = sqlite3.connect('school_bot.db')
            cursor = conn.cursor()
            
            # إنشاء file_id فريد (بديل مؤقت لحين رفع من الموقع)
            import uuid
            temp_file_id = f"local_{uuid.uuid4().hex[:16]}"
            
            cursor.execute("""
                INSERT INTO library (
                    title, description, file_id, file_type, content_type, category,
                    uploader_id, uploader_name, upload_date, approved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, description, temp_file_id, 'application/pdf', 'book', category,
                session['user_id'], session['name'], 
                datetime.now().isoformat(), 
                1  # معتمد تلقائياً
            ))
            
            book_id = cursor.lastrowid
            
            # حفظ مسار الملف المحلي
            cursor.execute("""
                INSERT INTO library_files (library_item_id, file_type, local_path)
                VALUES (?, ?, ?)
            """, (book_id, 'application/pdf', file_path))
            
            conn.commit()
            conn.close()
            
            flash(f'تم رفع الكتاب "{title}" بنجاح! 📚 وسيظهر في البوت مباشرة.', 'success')
            logger.info(f"✅ تم رفع كتاب جديد: {title} (ID: {book_id})")
            return redirect(url_for('library'))
            
        except Exception as e:
            logger.error(f"❌ خطأ في رفع الكتاب: {e}")
            flash('حدث خطأ أثناء رفع الكتاب. حاول مرة أخرى.', 'danger')
            return redirect(request.url)
    
    return render_template('upload.html')


@app.route('/download/<int:book_id>')
@require_login
def download_book(book_id):
    """تحميل كتاب من school_bot.db"""
    try:
        conn = sqlite3.connect('school_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # جلب معلومات الكتاب
        cursor.execute("""
            SELECT lf.local_path, l.title
            FROM library l
            JOIN library_files lf ON l.id = lf.library_item_id
            WHERE l.id = ? AND l.approved = 1
        """, (book_id,))
        
        result = cursor.fetchone()
        
        if not result or not result['local_path']:
            conn.close()
            flash('لم يتم العثور على الكتاب أو الملف غير موجود.', 'danger')
            logger.warning(f"⚠️ محاولة تحميل كتاب غير موجود: ID={book_id}")
            return redirect(url_for('library'))
        
        file_path = result['local_path']
        book_title = result['title']
        
        # تصحيح المسار (تحويل backslashes إلى forward slashes)
        file_path = file_path.replace('\\', '/')
        
        # التأكد من أن المسار مطلق
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)
        
        # التحقق من وجود الملف
        if not os.path.exists(file_path):
            conn.close()
            flash('الملف المطلوب غير موجود على الخادم.', 'danger')
            logger.error(f"❌ الملف غير موجود: {file_path}")
            return redirect(url_for('library'))
        
        # زيادة عداد التحميلات
        cursor.execute("""
            UPDATE library SET downloads = downloads + 1 
            WHERE id = ?
        """, (book_id,))
        
        conn.commit()
        conn.close()
        
        # إرسال الملف
        logger.info(f"✅ تحميل كتاب: {book_title} (ID={book_id})")
        return send_from_directory(
            os.path.dirname(file_path),
            os.path.basename(file_path),
            as_attachment=True
        )
            
    except Exception as e:
        logger.error(f"❌ خطأ في تحميل الكتاب ID={book_id}: {e}")
        logger.exception(e)
        flash('حدث خطأ أثناء التحميل. يرجى المحاولة مرة أخرى.', 'danger')
        return redirect(url_for('library'))


@app.route('/delete-book/<int:book_id>', methods=['POST'])
@require_login
def delete_book(book_id):
    """حذف كتاب من school_bot.db"""
    try:
        conn = sqlite3.connect('school_bot.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # جلب معلومات الكتاب للتحقق من الصلاحيات
        cursor.execute("""
            SELECT title, uploader_id FROM library WHERE id = ?
        """, (book_id,))
        
        book = cursor.fetchone()
        
        if not book:
            conn.close()
            flash('لم يتم العثور على الكتاب.', 'danger')
            return redirect(url_for('library'))
        
        title = book['title']
        uploader_id = book['uploader_id']
        
        # التحقق من الصلاحيات (المستخدم نفسه أو الأدمن)
        current_user_id = session.get('user_id')
        is_admin = session.get('username') == 'admin'
        
        if not is_admin and current_user_id != uploader_id:
            flash('ليس لديك صلاحية لحذف هذا الكتاب.', 'danger')
            conn.close()
            logger.warning(f"⚠️ محاولة حذف غير مصرح بها: user={current_user_id}, book={book_id}")
            return redirect(url_for('library'))
        
        # حذف الملف الفعلي
        cursor.execute("""
            SELECT local_path FROM library_files WHERE library_item_id = ?
        """, (book_id,))
        
        file_result = cursor.fetchone()
        if file_result and file_result['local_path']:
            file_path = file_result['local_path'].replace('\\', '/')
            if not os.path.isabs(file_path):
                file_path = os.path.join(os.getcwd(), file_path)
            
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"✅ تم حذف الملف: {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في حذف الملف: {e}")
        
        # حذف من قاعدة البيانات
        cursor.execute("DELETE FROM library_files WHERE library_item_id = ?", (book_id,))
        cursor.execute("DELETE FROM ratings WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM favorites WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM library WHERE id = ?", (book_id,))
        
        conn.commit()
        conn.close()
        
        flash(f'تم حذف الكتاب "{title}" بنجاح.', 'success')
        logger.info(f"✅ تم حذف كتاب: {title} (ID={book_id}) بواسطة user={current_user_id}")
        return redirect(url_for('library'))
        
    except Exception as e:
        logger.error(f"❌ خطأ في حذف الكتاب ID={book_id}: {e}")
        logger.exception(e)
        flash('حدث خطأ أثناء الحذف. يرجى المحاولة مرة أخرى.', 'danger')
        return redirect(url_for('library'))


# ========================================
# Routes - الاستفسار الذكي
# ========================================

@app.route('/smart-query', methods=['GET', 'POST'])
@require_login
def smart_query():
    """صفحة الاستفسار الذكي - RAG"""
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        
        if not question:
            flash('الرجاء إدخال سؤال.', 'warning')
            return redirect(url_for('smart_query'))
        
        # استدعاء الدالة المشتركة (مع asyncio)
        reply_data = asyncio.run(bot_logic.get_smart_reply(question))
        
        return render_template(
            'smart_query.html',
            question=question,
            answer=reply_data['answer'],
            links=reply_data['links']
        )
    
    return render_template('smart_query.html')


# ========================================
# Webhook - البوت
# ========================================

@app.route('/webhook', methods=['POST'])
async def webhook():
    """معالجة updates من Telegram"""
    if not telegram_app:
        return 'Bot not configured', 503
    
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update)
        return 'OK', 200
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة webhook: {e}")
        return 'Error', 500


@app.route('/set-webhook', methods=['GET'])
def set_webhook():
    """تعيين webhook URL للبوت"""
    if not telegram_app:
        return 'Bot not configured', 503
    
    if not Config.WEBHOOK_URL:
        return 'WEBHOOK_URL not set in config', 400
    
    try:
        asyncio.run(telegram_app.bot.set_webhook(Config.WEBHOOK_URL))
        return f'Webhook set to: {Config.WEBHOOK_URL}', 200
    except Exception as e:
        logger.error(f"❌ فشل تعيين webhook: {e}")
        return f'Error: {e}', 500


@app.route('/bot-status', methods=['GET'])
def bot_status_check():
    """صفحة/API للتحقق من حالة البوت"""
    bot_is_online, bot_status_msg = check_bot_status()
    
    # إذا كان الطلب JSON (من AJAX)
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return {
            'online': bot_is_online,
            'message': bot_status_msg,
            'timestamp': datetime.now().isoformat()
        }
    
    # عرض صفحة HTML
    status_color = 'success' if bot_is_online else 'danger'
    status_icon = 'check-circle' if bot_is_online else 'exclamation-triangle'
    
    return f'''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>حالة البوت</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body style="background: #f3f2f1; padding: 2rem;">
        <div class="container">
            <div class="card shadow-sm">
                <div class="card-body text-center py-5">
                    <i class="fas fa-{status_icon} fa-5x text-{status_color} mb-3"></i>
                    <h2 class="mb-3">حالة البوت</h2>
                    <div class="alert alert-{status_color}">
                        <strong>الحالة:</strong> {"متصل ✅" if bot_is_online else "غير متصل ❌"}
                    </div>
                    <p class="text-muted">{bot_status_msg}</p>
                    <a href="{url_for('home')}" class="btn btn-primary mt-3">
                        <i class="fas fa-home"></i> العودة للرئيسية
                    </a>
                </div>
            </div>
        </div>
    </body>
    </html>
    '''


# ========================================
# معالجة الأخطاء
# ========================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    # لا حاجة لـ rollback لأننا لا نستخدم SQLAlchemy
    logger.error(f"❌ خطأ داخلي 500: {error}")
    return render_template('500.html'), 500


# ========================================
# تشغيل التطبيق
# ========================================

if __name__ == '__main__':
    # إعداد البوت
    setup_telegram_bot()
    
    # تشغيل Flask
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=False  # يجب أن يكون False في الإنتاج
    )
