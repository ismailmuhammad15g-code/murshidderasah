# 🚀 دليل النشر على PythonAnywhere

## ✅ الخطوات

### 1️⃣ إنشاء حساب على PythonAnywhere
اذهب إلى: https://www.pythonanywhere.com/registration/register/beginner/

### 2️⃣ فتح Bash Console
من Dashboard → New Console → Bash

### 3️⃣ استنساخ المشروع
```bash
git clone https://github.com/ismailmuhammad15g-code/murshidderasah.git
cd murshidderasah
```

### 4️⃣ إنشاء Virtual Environment
```bash
mkvirtualenv --python=python3.10 murshid
```

### 5️⃣ تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 6️⃣ إنشاء ملف .env
```bash
nano .env
```

أضف المحتوى التالي (استبدل بمفاتيحك):
```env
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
GOOGLE_API_KEY_1=YOUR_API_KEY_1
GOOGLE_API_KEY_2=YOUR_API_KEY_2
ADMIN_NAME=your_name
ADMIN_EMAIL=your_email@example.com
WEBHOOK_URL=https://YOUR_USERNAME.pythonanywhere.com/webhook
HOST=0.0.0.0
PORT=8080
```

اضغط `Ctrl+X` ثم `Y` ثم `Enter`

### 7️⃣ تهيئة قاعدة البيانات
```bash
python -c "from database import init_db; init_db()"
```

### 8️⃣ إعداد Web App
من Dashboard → Web → Add a new web app
- اختر: **Manual configuration**
- Python version: **3.10**

### 9️⃣ تكوين WSGI
اضغط على WSGI configuration file وعدّله:

```python
import sys
import os

# إضافة مسار المشروع
path = '/home/YOUR_USERNAME/murshidderasah'
if path not in sys.path:
    sys.path.append(path)

# تحميل المتغيرات البيئية
from dotenv import load_dotenv
project_folder = os.path.expanduser(path)
load_dotenv(os.path.join(project_folder, '.env'))

# استيراد التطبيق
from flask_app import app as application
```

**ملاحظة**: استبدل `YOUR_USERNAME` باسم المستخدم الخاص بك

### 🔟 تكوين Virtual Environment في Web App
في صفحة Web:
- **Virtualenv**: `/home/YOUR_USERNAME/.virtualenvs/murshid`

### 1️⃣1️⃣ إعادة تحميل Web App
اضغط الزر الأخضر: **Reload YOUR_USERNAME.pythonanywhere.com**

---

## 🎯 الوصول للموقع

موقعك سيكون: `https://YOUR_USERNAME.pythonanywhere.com`

---

## 🔧 استكشاف الأخطاء

### إذا ظهرت أخطاء:
1. تحقق من **Error log** في صفحة Web
2. تأكد أن `.env` موجود ويحتوي على جميع المفاتيح
3. تأكد أن Virtual Environment مُفعّل بشكل صحيح

### لعرض السجلات:
```bash
tail -f /var/log/YOUR_USERNAME.pythonanywhere.com.error.log
```

---

## 📝 ملاحظات مهمة

1. **الحساب المجاني** يدعم:
   - تطبيق Flask واحد
   - 512MB RAM
   - بطيء قليلاً لكن كافٍ للتجربة

2. **Webhook للبوت**:
   - تأكد أن `WEBHOOK_URL` في `.env` صحيح
   - شغّل `python set_webhook.py` بعد النشر

3. **قاعدة البيانات**:
   - ملف `db/` موجود في المشروع
   - سيعمل تلقائياً

---

✅ **انتهى! موقعك الآن على الإنترنت!**
