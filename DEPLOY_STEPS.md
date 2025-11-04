# 🚀 خطوات النشر على PythonAnywhere بعد Google Drive Integration

## ⚠️ خطوات مهمة يجب القيام بها

### 1️⃣ سحب التحديثات من GitHub

```bash
cd /home/ismailmohammed/murshidderasah
git pull origin main
```

إذا واجهت مشاكل:

```bash
git stash
git pull origin main
```

---

### 2️⃣ تثبيت المكتبات الجديدة

```bash
pip install --user google-api-python-client==2.108.0 google-auth-httplib2==0.2.0 google-auth-oauthlib==1.2.0
```

أو:

```bash
pip install --user -r requirements.txt
```

---

### 3️⃣ تحديث قاعدة البيانات

```bash
python add_drive_link_column.py
```

**يجب أن ترى:** ✅ تم إضافة عمود drive_link بنجاح!

---

### 4️⃣ إضافة Service Account JSON في `.env`

افتح `.env` وأضف:

```bash
GOOGLE_SERVICE_ACCOUNT_JSON='<محتوى ملف murshidderasah-950af6007108.json كامل>'
```

**كيفية الحصول على المحتوى:**

1. افتح ملف `murshidderasah-950af6007108.json` من جهازك المحلي
2. انسخ **كل المحتوى** (يبدأ بـ `{"type":"service_account"...` وينتهي بـ `...}`)
3. ضعه بين علامتي اقتباس مفردة `'...'` بعد `=`

⚠️ **مهم جداً:** الـ JSON كاملاً في سطر واحد، أو استخدم escape للأسطر الجديدة.

---

### 5️⃣ نقل الكتب الموجودة (اختياري)

إذا كان لديك كتب قديمة في `static/uploads/`:

```bash
python migrate_existing_books.py
```

اكتب `y` للمتابعة.

**ملاحظة:** هذا سيرفع جميع الكتب القديمة إلى Google Drive.

---

### 6️⃣ إعادة تشغيل التطبيق

على PythonAnywhere:

1. اذهب إلى تبويب **Web**
2. اضغط **Reload**
3. تحقق من عدم وجود أخطاء في error log

---

## ✅ اختبار النظام

1. سجل دخول في الموقع
2. اذهب إلى صفحة `/upload`
3. حمّل ملف PDF
4. يجب أن ترى: "تم رفع الكتاب بنجاح إلى Google Drive! 📚☁️"

---

## 🔍 استكشاف الأخطاء

### خطأ: `No module named 'googleapiclient'`

```bash
pip install --user --upgrade google-api-python-client
```

### خطأ: `File not found: murshidderasah-950af6007108.json`

تأكد من إضافة `GOOGLE_SERVICE_ACCOUNT_JSON` في `.env` بشكل صحيح.

### خطأ: `403 Forbidden`

تحقق من أن المجلد `1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH` مشارك مع:
`murshidderasah@murshidderasah.iam.gserviceaccount.com`

---

## 📊 التحقق من قاعدة البيانات

```bash
python -c "import sqlite3; conn=sqlite3.connect('school_bot.db'); c=conn.cursor(); c.execute('PRAGMA table_info(library_files)'); print([row[1] for row in c.fetchall()])"
```

**يجب أن ترى:** `drive_link` في القائمة.

---

## 🎯 الملفات المُضافة/المُعدّلة

✅ `drive_uploader.py` (جديد)
✅ `add_drive_link_column.py` (جديد)
✅ `migrate_existing_books.py` (جديد)
✅ `GOOGLE_DRIVE_INTEGRATION.md` (جديد)
✅ `flask_app.py` (معدّل - دالة upload_book)
✅ `requirements.txt` (معدّل - مكتبات جديدة)
✅ `.gitignore` (معدّل - حماية ملفات JSON)

---

**تاريخ:** 2024
**الحالة:** ✅ جاهز للنشر
