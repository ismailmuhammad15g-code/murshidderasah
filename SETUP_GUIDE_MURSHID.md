# 🚀 دليل إعداد murshidderasah.pythonanywhere.com

## 📌 معلوماتك
- **اسم المستخدم**: `murshidderasah`
- **رابط الموقع**: https://murshidderasah.pythonanywhere.com
- **مسار المشروع**: `/home/murshidderasah/murshidderasah`

---

## 🎯 الخطوات (بالتفصيل)

### 1️⃣ في Bash Console

افتح Bash Console من PythonAnywhere ونفذ:

```bash
# استنساخ المشروع (إذا لم يكن موجوداً)
git clone https://github.com/ismailmuhammad15g-code/murshidderasah.git
cd murshidderasah

# إنشاء Virtual Environment
mkvirtualenv --python=python3.10 murshid

# تثبيت المكتبات
pip install -r requirements.txt

# إنشاء ملف .env
nano .env
```

### 2️⃣ محتوى ملف .env

**انسخ هذا بالضبط** (استبدل المفاتيح الحقيقية):

```env
# بوت تليجرام
BOT_TOKEN=YOUR_REAL_BOT_TOKEN_HERE

# مفاتيح Google API
GOOGLE_API_KEY_1=YOUR_REAL_GOOGLE_KEY_HERE
GOOGLE_API_KEY_2=YOUR_SECOND_KEY_IF_YOU_HAVE

# معلومات الأدمن
ADMIN_NAME=your_name
ADMIN_EMAIL=your_email@example.com

# إعدادات Flask (لا تغير هذه!)
WEBHOOK_URL=https://murshidderasah.pythonanywhere.com/webhook
HOST=0.0.0.0
PORT=8080

# قاعدة البيانات
DB_PATH=./db
```

**بعد الانتهاء:**
- اضغط `Ctrl+X`
- اضغط `Y`
- اضغط `Enter`

### 3️⃣ تهيئة قاعدة البيانات

```bash
python -c "from database import init_db; init_db()"
```

---

## 🌐 في صفحة Web App

اذهب إلى: https://www.pythonanywhere.com/user/murshidderasah/webapps/

### 📁 Code Section

**احذف المحتوى القديم** وضع هذه بالضبط:

| الحقل | القيمة |
|------|--------|
| **Source code** | `/home/murshidderasah/murshidderasah` |
| **Working directory** | `/home/murshidderasah/murshidderasah` |

### 🐍 Virtualenv Section

| الحقل | القيمة |
|------|--------|
| **Virtualenv** | `/home/murshidderasah/.virtualenvs/murshid` |

⚠️ **انتبه:** `.virtualenvs` يبدأ بنقطة!

---

## 📝 WSGI Configuration File

### 1️⃣ افتح الملف
اضغط على الرابط الأزرق:
```
/var/www/murshidderasah_pythonanywhere_com_wsgi.py
```

### 2️⃣ احذف كل المحتوى القديم

### 3️⃣ انسخ هذا الكود بالضبط

```python
# =========================================
# WSGI Configuration for murshidderasah
# =========================================

import sys
import os

# === 1. مسار المشروع ===
path = '/home/murshidderasah/murshidderasah'

# إضافة المسار
if path not in sys.path:
    sys.path.insert(0, path)

# === 2. تحميل .env ===
from dotenv import load_dotenv
project_folder = os.path.expanduser(path)
load_dotenv(os.path.join(project_folder, '.env'))

# === 3. استيراد Flask ===
from flask_app import app as application

# === 4. تفعيل السجلات ===
import logging
logging.basicConfig(level=logging.INFO)
```

### 4️⃣ احفظ
اضغط الزر الأخضر **"Save"** في الأعلى

---

## 🚀 التشغيل

### 1️⃣ اضغط الزر الأخضر الكبير
```
[🔄 Reload murshidderasah.pythonanywhere.com]
```

### 2️⃣ انتظر 5-10 ثواني

### 3️⃣ افتح الموقع
```
https://murshidderasah.pythonanywhere.com
```

---

## ✅ Checklist قبل Reload

تأكد من:

- [ ] Source code = `/home/murshidderasah/murshidderasah`
- [ ] Working directory = `/home/murshidderasah/murshidderasah`  
- [ ] Virtualenv = `/home/murshidderasah/.virtualenvs/murshid`
- [ ] WSGI file محدّث بالكود الجديد
- [ ] ملف `.env` موجود وفيه المفاتيح الصحيحة

---

## 🔧 إذا ظهرت مشاكل

### مشكلة: "Something went wrong"

**اذهب إلى:**
1. صفحة Web
2. اضغط **"Error log"** (رابط أحمر في الأعلى)
3. اقرأ آخر خطأ

**الأخطاء الشائعة:**

#### `ModuleNotFoundError: No module named 'flask_app'`
**الحل:** تحقق أن المسارات صحيحة في WSGI

#### `ModuleNotFoundError: No module named 'dotenv'`
**الحل:** افتح Bash Console:
```bash
workon murshid
cd murshidderasah
pip install -r requirements.txt
```

#### `No such file or directory: '.env'`
**الحل:**
```bash
cd /home/murshidderasah/murshidderasah
nano .env
# أضف المحتوى من الخطوة 2
```

---

## 🔗 الروابط المهمة

- **الموقع**: https://murshidderasah.pythonanywhere.com
- **Web App Settings**: https://www.pythonanywhere.com/user/murshidderasah/webapps/
- **Bash Console**: https://www.pythonanywhere.com/user/murshidderasah/consoles/
- **Error Log**: في صفحة Web App (رابط أحمر)

---

## 🎯 للبوت على Telegram

بعد نجاح الموقع، شغّل هذا في Bash Console:

```bash
workon murshid
cd murshidderasah
python set_webhook.py
```

---

✅ **بالتوفيق! كل شيء واضح الآن!** 🚀
