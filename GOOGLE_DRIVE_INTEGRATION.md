# 📚☁️ تكامل Google Drive لتخزين الكتب

## نظرة عامة

تم استبدال نظام تخزين الكتب المحلي (`static/uploads`) بالكامل بنظام **Google Drive API**. الآن يتم رفع جميع الكتب الجديدة تلقائياً إلى Google Drive بدلاً من تخزينها محلياً على السيرفر.

---

## ✅ المزايا

1. **لا حاجة للتخزين المحلي**: توفير مساحة السيرفر
2. **سرعة أفضل**: Google Drive CDN عالي الأداء
3. **موثوقية أعلى**: نسخ احتياطي تلقائي من Google
4. **سهولة الإدارة**: إمكانية إدارة الملفات من Google Drive مباشرة
5. **روابط دائمة**: روابط ثابتة لا تتغير

---

## 📋 التغييرات المُنفذة

### 1. تحديث `requirements.txt`

أضيفت المكتبات التالية:

```txt
google-api-python-client==2.108.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.0
```

قم بتثبيتها:

```bash
pip install -r requirements.txt
```

---

### 2. إنشاء `drive_uploader.py`

ملف جديد يحتوي على منطق الاتصال بـ Google Drive:

**الوظائف الرئيسية:**

- `get_drive_service()`: المصادقة والاتصال بـ Google Drive API
- `upload_book(file_path)`: رفع كتاب وإرجاع رابط Google Drive

**المصادقة الذكية:**

1. يحاول أولاً قراءة `GOOGLE_SERVICE_ACCOUNT_JSON` من متغيرات البيئة (للبيئة الإنتاجية)
2. إذا فشل، يستخدم الملف المحلي `murshidderasah-950af6007108.json` (للبيئة التطويرية)

---

### 3. تعديل `flask_app.py` - دالة `upload_book()`

**السطور المُعدلة:** 551-640

**التدفق الجديد:**

1. حفظ الملف مؤقتاً في `/tmp/uploads/`
2. رفع الملف إلى Google Drive باستخدام `drive_uploader.upload_book()`
3. حذف الملف المؤقت
4. حفظ رابط Google Drive في قاعدة البيانات

**مثال على الكود:**

```python
from drive_uploader import upload_book as upload_to_drive

# حفظ مؤقت
temp_path = "/tmp/uploads/temp_file.pdf"
file.save(temp_path)

# رفع إلى Google Drive
drive_link = upload_to_drive(temp_path)

# حذف المؤقت
os.remove(temp_path)

# حفظ في قاعدة البيانات
cursor.execute("""
    INSERT INTO library_files (library_item_id, file_type, local_path, drive_link)
    VALUES (?, ?, ?, ?)
""", (book_id, 'application/pdf', '', drive_link))
```

---

### 4. تحديث قاعدة البيانات

**إضافة عمود `drive_link`** إلى جدول `library_files`:

```bash
python add_drive_link_column.py
```

**هيكل الجدول الجديد:**

```sql
CREATE TABLE library_files (
    id INTEGER PRIMARY KEY,
    library_item_id INTEGER,
    file_id TEXT,
    file_type TEXT,
    file_order INTEGER DEFAULT 0,
    caption TEXT,
    local_path TEXT,          -- أصبح فارغاً للكتب الجديدة
    drive_link TEXT           -- عمود جديد يحتوي رابط Google Drive
)
```

---

### 5. نقل الكتب الموجودة (Migration Script)

**استخدم** `migrate_existing_books.py` لنقل الكتب المحلية القديمة:

```bash
python migrate_existing_books.py
```

**ماذا يفعل؟**

1. يقرأ جميع الكتب من `library_files` التي لها `local_path` ولا يوجد لها `drive_link`
2. يرفع كل كتاب إلى Google Drive
3. يحدّث قاعدة البيانات بالرابط الجديد
4. (اختياري) يحذف الملف المحلي بعد النقل الناجح

---

## 🔐 إعداد Google Drive API

### للبيئة المحلية (Local Development)

ضع ملف `murshidderasah-950af6007108.json` في مجلد المشروع الجذر.

### للبيئة الإنتاجية (PythonAnywhere / Production)

أضف متغير بيئة:

```bash
GOOGLE_SERVICE_ACCOUNT_JSON='{
  "type": "service_account",
  "project_id": "murshidderasah",
  "private_key_id": "...",
  "private_key": "...",
  ...
}'
```

**على PythonAnywhere:**

1. افتح `.env` file
2. أضف السطر:
   ```
   GOOGLE_SERVICE_ACCOUNT_JSON='<محتوى JSON كامل>'
   ```
3. احفظ وأعد تشغيل التطبيق

---

## 📂 معلومات Google Drive

- **Folder ID:** `1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH`
- **الملفات المرفوعة:** تكون **قابلة للقراءة للجميع** (anyone with the link)
- **نوع الرابط:** `https://drive.google.com/file/d/FILE_ID/view`

---

## 🧪 اختبار التكامل

### 1. اختبار الرفع

```bash
python -c "from drive_uploader import upload_book; print(upload_book('test.pdf'))"
```

### 2. اختبار عبر الموقع

1. سجل دخول في الموقع
2. اذهب إلى صفحة `/upload`
3. حمّل ملف PDF
4. تحقق من ظهور رسالة "تم رفع الكتاب بنجاح إلى Google Drive! 📚☁️"
5. افحص قاعدة البيانات:

```bash
python -c "import sqlite3; conn=sqlite3.connect('school_bot.db'); c=conn.cursor(); c.execute('SELECT drive_link FROM library_files ORDER BY id DESC LIMIT 1'); print(c.fetchone())"
```

---

## 🐛 استكشاف الأخطاء

### خطأ: `403 Forbidden`

- **السبب:** Service Account ليس لديه صلاحيات على المجلد
- **الحل:** شارك المجلد `1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH` مع البريد الإلكتروني للـ Service Account

### خطأ: `File not found: murshidderasah-950af6007108.json`

- **السبب:** الملف غير موجود أو متغير البيئة غير مضبوط
- **الحل:** 
  - **محلياً:** تأكد من وجود الملف في مجلد المشروع
  - **إنتاج:** تأكد من ضبط `GOOGLE_SERVICE_ACCOUNT_JSON` في `.env`

### خطأ: `No module named 'googleapiclient'`

- **الحل:** 
  ```bash
  pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
  ```

---

## 📊 قاعدة البيانات - مثال

**قبل التكامل:**

```sql
SELECT local_path FROM library_files WHERE id = 1;
-- Result: "static/uploads/book1.pdf"
```

**بعد التكامل:**

```sql
SELECT drive_link FROM library_files WHERE id = 1;
-- Result: "https://drive.google.com/file/d/1A2B3C4D5E6F7G8H/view"
```

---

## ✨ الخطوات التالية

- [ ] تشغيل `migrate_existing_books.py` لنقل الكتب القديمة
- [ ] اختبار رفع كتاب جديد من الموقع
- [ ] تحديث البوت ليستخدم روابط Google Drive بدلاً من المسارات المحلية
- [ ] (اختياري) حذف مجلد `static/uploads/` بعد التأكد من نقل جميع الكتب

---

## 🎯 ملخص

✅ **تم الانتهاء من:**

1. إضافة مكتبات Google Drive API
2. إنشاء `drive_uploader.py` للاتصال بـ Google Drive
3. تعديل `flask_app.py` لرفع الكتب إلى Google Drive
4. إضافة عمود `drive_link` في قاعدة البيانات
5. إنشاء script هجرة الكتب القديمة

⏳ **يتطلب إجراء يدوي:**

- تشغيل `python migrate_existing_books.py` لنقل الكتب الموجودة

---

**تاريخ التحديث:** 2024
**الحالة:** ✅ جاهز للاستخدام
