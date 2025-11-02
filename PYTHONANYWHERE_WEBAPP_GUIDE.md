# 🌐 دليل إعداد Web App على PythonAnywhere - شرح مفصل

## 📌 المقدمة
هذا الدليل يشرح **بالتفصيل الممل** كل خطوة لإعداد Flask Web App على PythonAnywhere.
كل حقل، كل زر، كل إعداد - موضّح بالكامل!

---

## 🎯 الجزء الأول: التحضير (في Bash Console)

### 1️⃣ فتح Bash Console
- اذهب إلى Dashboard
- اضغط على **"Consoles"** (في القائمة العلوية)
- اضغط على **"$ Bash"** (زر أخضر)

### 2️⃣ استنساخ المشروع
في الـ Console، اكتب:
```bash
git clone https://github.com/ismailmuhammad15g-code/murshidderasah.git
```

انتظر حتى ينتهي التحميل، ستشاهد:
```
Cloning into 'murshidderasah'...
...
done.
```

### 3️⃣ الدخول للمشروع
```bash
cd murshidderasah
```

### 4️⃣ إنشاء Virtual Environment
```bash
mkvirtualenv --python=python3.10 murshid
```

**ملاحظة مهمة:** بعد تنفيذ هذا الأمر، سيظهر `(murshid)` قبل الـ prompt

### 5️⃣ تثبيت المكتبات
```bash
pip install -r requirements.txt
```

انتظر 2-3 دقائق حتى ينتهي التثبيت.

### 6️⃣ إنشاء ملف .env
```bash
nano .env
```

**داخل nano:**
1. اكتب المحتوى التالي (استبدل بمفاتيحك الحقيقية):

```env
# بوت تليجرام
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789

# مفاتيح Google API (ضع على الأقل مفتاح واحد)
GOOGLE_API_KEY_1=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
GOOGLE_API_KEY_2=AIzaSyYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY

# معلومات الأدمن
ADMIN_NAME=اسمك_هنا
ADMIN_EMAIL=your_email@example.com

# إعدادات Flask
WEBHOOK_URL=https://YOUR_USERNAME.pythonanywhere.com/webhook
HOST=0.0.0.0
PORT=8080

# قاعدة البيانات
DB_PATH=./db
```

2. اضغط `Ctrl+X`
3. اضغط `Y` (نعم)
4. اضغط `Enter` (حفظ)

**ملاحظة مهمة جداً:** استبدل `YOUR_USERNAME` باسم المستخدم الخاص بك في PythonAnywhere!

### 7️⃣ تهيئة قاعدة البيانات
```bash
python -c "from database import init_db; init_db()"
```

إذا نجح، لن ترى أي رسالة خطأ.

### 8️⃣ التحقق من المسار
```bash
pwd
```

يجب أن يظهر شيء مثل:
```
/home/YOUR_USERNAME/murshidderasah
```

**احفظ هذا المسار! ستحتاجه لاحقاً.**

---

## 🌐 الجزء الثاني: إعداد Web App

### 1️⃣ الذهاب إلى صفحة Web
- من Dashboard (الصفحة الرئيسية)
- اضغط على **"Web"** (في القائمة العلوية)

### 2️⃣ إضافة Web App جديد
- اضغط على الزر الأزرق: **"Add a new web app"**

### 3️⃣ اختيار Domain
**سيظهر لك:**
```
Your web app will be available at:
YOUR_USERNAME.pythonanywhere.com
```

- اضغط **"Next"** (أزرق)

### 4️⃣ اختيار Framework
**سيظهر لك قائمة:**
- Flask
- Django
- web2py
- Bottle
- **Manual configuration** ← اختر هذا!

اضغط على **"Manual configuration"** (بدون أي framework)

### 5️⃣ اختيار Python Version
**سيظهر لك قائمة:**
- Python 3.11
- Python 3.10 ← **اختر هذا!**
- Python 3.9
- Python 3.8

اضغط على **"Python 3.10"**

### 6️⃣ تأكيد
- اضغط **"Next"** (أزرق)

---

## ⚙️ الجزء الثالث: تكوين Web App

الآن أنت في صفحة إعدادات Web App. سنملأ كل قسم بالتفصيل:

### 📁 القسم الأول: Code Section

#### 1️⃣ Source code:
**الحقل:**
```
Source code:
[_________________________________]
```

**املأه بـ:**
```
/home/YOUR_USERNAME/murshidderasah
```

**مثال (إذا كان اسمك ismail):**
```
/home/ismail/murshidderasah
```

**ملاحظة:** استبدل `YOUR_USERNAME` باسم المستخدم الحقيقي!

#### 2️⃣ Working directory:
**الحقل:**
```
Working directory:
[_________________________________]
```

**املأه بـ نفس المسار:**
```
/home/YOUR_USERNAME/murshidderasah
```

---

### 🐍 القسم الثاني: Virtualenv Section

#### Virtualenv:
**الحقل:**
```
Virtualenv:
[_________________________________]
```

**املأه بـ:**
```
/home/YOUR_USERNAME/.virtualenvs/murshid
```

**مثال (إذا كان اسمك ismail):**
```
/home/ismail/.virtualenvs/murshid
```

**ملاحظة:** 
- `.virtualenvs` يبدأ بنقطة!
- `murshid` هو اسم الـ virtualenv الذي أنشأناه في الخطوة 4 من الجزء الأول

---

### 📝 القسم الثالث: WSGI Configuration File

هذا **أهم** قسم!

#### 1️⃣ ابحث عن السطر:
```
WSGI configuration file:
/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py
```

#### 2️⃣ اضغط على الرابط الأزرق (اسم الملف)

سيفتح محرر نصوص. **احذف كل المحتوى!**

#### 3️⃣ اكتب المحتوى التالي بالضبط:

```python
# =========================================
# WSGI Configuration for murshidderasah
# =========================================

import sys
import os

# === 1. تعريف مسار المشروع ===
# استبدل YOUR_USERNAME باسم المستخدم الخاص بك
path = '/home/YOUR_USERNAME/murshidderasah'

# إضافة المسار إلى sys.path
if path not in sys.path:
    sys.path.insert(0, path)

# === 2. تحميل المتغيرات البيئية من .env ===
from dotenv import load_dotenv
project_folder = os.path.expanduser(path)
load_dotenv(os.path.join(project_folder, '.env'))

# === 3. استيراد تطبيق Flask ===
from flask_app import app as application

# === 4. تمكين السجلات (اختياري - للتشخيص) ===
import logging
logging.basicConfig(level=logging.INFO)
```

**⚠️ مهم جداً:**
- استبدل `YOUR_USERNAME` في السطر 9 باسم المستخدم الحقيقي!
- **مثال:** إذا كان اسمك `ismail`، اكتب:
  ```python
  path = '/home/ismail/murshidderasah'
  ```

#### 4️⃣ حفظ الملف
- اضغط الزر الأخضر في الأعلى: **"Save"**

---

### 🔄 القسم الرابع: Static Files (اختياري)

**هذا القسم اختياري** - للصور، CSS، JavaScript

إذا أردت إضافة static files:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOUR_USERNAME/murshidderasah/static` |

---

### 🔐 القسم الخامس: Security (اختياري)

#### Force HTTPS:
- يمكنك تفعيله بتحديد المربع ✓
- هذا يجبر الموقع على استخدام HTTPS (آمن)

---

## 🚀 الجزء الرابع: التشغيل!

### 1️⃣ إعادة تحميل Web App
في أعلى الصفحة، ستجد زر أخضر كبير:
```
[🔄 Reload YOUR_USERNAME.pythonanywhere.com]
```

**اضغط عليه!**

### 2️⃣ الانتظار
انتظر 5-10 ثواني...

### 3️⃣ فتح الموقع
اضغط على الرابط في الأعلى:
```
🔗 YOUR_USERNAME.pythonanywhere.com
```

---

## ✅ التحقق من النجاح

### إذا نجح:
- سيفتح الموقع بشكل طبيعي
- سترى الصفحة الرئيسية

### إذا فشل:
اقرأ قسم "استكشاف الأخطاء" أدناه ⬇️

---

## 🔧 استكشاف الأخطاء

### مشكلة 1: "Something went wrong :("

**السبب:** خطأ في الكود أو الإعدادات

**الحل:**
1. اذهب إلى صفحة Web
2. اضغط على **"Error log"** (في الأعلى - رابط أحمر)
3. ستشاهد السجل - ابحث عن آخر خطأ
4. اقرأ رسالة الخطأ بعناية

**الأخطاء الشائعة:**

#### خطأ: `ModuleNotFoundError: No module named 'flask_app'`
**السبب:** مسار Source code خاطئ أو WSGI خاطئ

**الحل:**
- تأكد أن Source code يشير إلى: `/home/YOUR_USERNAME/murshidderasah`
- تأكد أن `YOUR_USERNAME` صحيح!

#### خطأ: `ModuleNotFoundError: No module named 'dotenv'`
**السبب:** Virtualenv غير مفعّل أو المكتبات غير مثبتة

**الحل:**
1. افتح Bash Console
2. شغّل:
   ```bash
   workon murshid
   cd murshidderasah
   pip install -r requirements.txt
   ```

#### خطأ: `No such file or directory: '.env'`
**السبب:** ملف `.env` غير موجود

**الحل:**
```bash
cd /home/YOUR_USERNAME/murshidderasah
nano .env
# أضف المحتوى (راجع الخطوة 6 من الجزء الأول)
```

---

### مشكلة 2: الموقع بطيء جداً

**السبب:** الحساب المجاني محدود (512MB RAM)

**الحل:**
- هذا طبيعي للحساب المجاني
- يمكنك الترقية للحساب المدفوع

---

### مشكلة 3: البوت لا يرد في Telegram

**السبب:** Webhook غير مضبوط

**الحل:**
1. افتح Bash Console
2. شغّل:
   ```bash
   workon murshid
   cd murshidderasah
   python set_webhook.py
   ```

---

## 📋 ملخص - Checklist

قبل الضغط على Reload، تأكد:

- [ ] Source code: `/home/YOUR_USERNAME/murshidderasah`
- [ ] Working directory: `/home/YOUR_USERNAME/murshidderasah`
- [ ] Virtualenv: `/home/YOUR_USERNAME/.virtualenvs/murshid`
- [ ] WSGI file معدّل وفيه `path = '/home/YOUR_USERNAME/murshidderasah'`
- [ ] ملف `.env` موجود وفيه كل المفاتيح
- [ ] `YOUR_USERNAME` مستبدل في كل مكان!

---

## 🎉 النتيجة

بعد إتمام كل الخطوات، موقعك سيكون:

```
https://YOUR_USERNAME.pythonanywhere.com
```

والبوت سيعمل على Telegram عبر Webhook!

---

## 📞 دعم إضافي

إذا واجهت مشاكل:
1. راجع Error log في صفحة Web
2. تحقق من Bash Console
3. تأكد أن جميع المسارات صحيحة

---

✅ **بالتوفيق! موقعك الآن على الإنترنت!** 🚀
