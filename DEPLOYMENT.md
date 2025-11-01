# 🚀 دليل النشر على PythonAnywhere

دليل خطوة بخطوة لرفع مشروع "بوابة مرشد الدراسة" على PythonAnywhere.

## 📋 المتطلبات الأساسية

- حساب على PythonAnywhere (المجاني يكفي)
- قاعدة بيانات ChromaDB جاهزة في مجلد `./db`
- جميع المفاتيح API (Telegram + Gemini)

## 🔧 خطوات النشر

### 1. إنشاء حساب PythonAnywhere

1. اذهب إلى: https://www.pythonanywhere.com
2. أنشئ حساب مجاني (Beginner Account)
3. سجّل الدخول

### 2. رفع الملفات

#### الطريقة الأولى: Git (موصى بها)

في **Bash Console** على PythonAnywhere:

```bash
cd ~
git clone https://github.com/your-username/schoolnewsbot2.git
cd schoolnewsbot2
```

#### الطريقة الثانية: الرفع المباشر

1. اذهب إلى **Files** Tab
2. ارفع الملفات واحداً تلو الآخر
3. **مهم**: ارفع مجلد `db` (قاعدة ChromaDB) كاملاً

### 3. إعداد البيئة الافتراضية

في **Bash Console**:

```bash
cd ~/schoolnewsbot2
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

⚠️ **ملاحظة**: قد تستغرق عملية التثبيت 5-10 دقائق.

### 4. إعداد ملف .env

```bash
nano .env
```

أضف المتغيرات التالية:

```env
BOT_TOKEN=your_bot_token
WEBHOOK_URL=https://your-username.pythonanywhere.com/webhook

GOOGLE_API_KEY_1=your_key_1
GOOGLE_API_KEY_2=your_key_2
# ... إلخ (10 مفاتيح)

FLASK_SECRET_KEY=your-random-secret-key

# اختياري
HOST=0.0.0.0
PORT=8080
```

احفظ بـ: `Ctrl+X` ثم `Y` ثم `Enter`

### 5. إعداد Web App

1. اذهب إلى **Web** Tab
2. اضغط **Add a new web app**
3. اختر: **Flask**
4. اختر: **Python 3.10**
5. Path: `/home/your-username/schoolnewsbot2/flask_app.py`

### 6. تعديل ملف WSGI

في **Web** Tab، اضغط على ملف WSGI Configuration:

```python
import sys
import os

# إضافة مسار المشروع
path = '/home/your-username/schoolnewsbot2'
if path not in sys.path:
    sys.path.insert(0, path)

# تفعيل البيئة الافتراضية
activate_this = '/home/your-username/schoolnewsbot2/venv/bin/activate_this.py'
with open(activate_this) as file_:
    exec(file_.read(), dict(__file__=activate_this))

# استيراد التطبيق
from flask_app import app as application
```

احفظ الملف.

### 7. إعداد Static Files

في **Web** Tab، قسم **Static files**:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/your-username/schoolnewsbot2/static/` |

### 8. Reload التطبيق

في **Web** Tab، اضغط الزر الأخضر الكبير: **Reload your-username.pythonanywhere.com**

### 9. تعيين Webhook للبوت

افتح المتصفح واذهب إلى:

```
https://your-username.pythonanywhere.com/set-webhook
```

يجب أن ترى رسالة: `Webhook set to: https://your-username.pythonanywhere.com/webhook`

### 10. اختبار المشروع

#### الموقع:
```
https://your-username.pythonanywhere.com
```
- سجّل دخول: `admin` / `admin123`
- جرّب المكتبة والاستفسار الذكي

#### البوت:
1. افتح Telegram
2. ابحث عن البوت الخاص بك
3. أرسل `/start`
4. جرّب طرح سؤال

## 🐛 حل المشاكل الشائعة

### خطأ: "ModuleNotFoundError"

```bash
# في Bash Console
cd ~/schoolnewsbot2
source venv/bin/activate
pip install [اسم المكتبة الناقصة]
```

ثم Reload التطبيق.

### خطأ: "Database not found"

تأكد من رفع مجلد `db` بالكامل:

```bash
# في Bash Console
cd ~/schoolnewsbot2
ls -la db/
# يجب أن ترى ملفات ChromaDB
```

### البوت لا يستجيب

1. تحقق من صحة `BOT_TOKEN` في `.env`
2. تأكد من تعيين Webhook:
   ```
   https://your-username.pythonanywhere.com/set-webhook
   ```
3. تحقق من Error Log في **Web** Tab

### الموقع بطيء

الخطة المجانية محدودة:
- 100 ثانية CPU يومياً
- حلول:
  - استخدم Caching للنتائج المكررة
  - قلل عدد استدعاءات API
  - ترقية للخطة المدفوعة ($5/شهر)

## 📊 مراقبة الأداء

### Error Log
في **Web** Tab > **Log files** > **Error log**

### Access Log
في **Web** Tab > **Log files** > **Access log**

### Bash Commands للمراقبة

```bash
# عرض آخر 50 سطر من Error Log
tail -n 50 /var/log/your-username.pythonanywhere.com.error.log

# مراقبة الـ logs في الوقت الفعلي
tail -f /var/log/your-username.pythonanywhere.com.error.log
```

## 🔄 التحديثات المستقبلية

عند تحديث الكود:

```bash
cd ~/schoolnewsbot2
git pull  # إذا كنت تستخدم Git
# أو ارفع الملفات المعدلة يدوياً

# ثم Reload في Web Tab
```

## 🔐 الأمان

- ✅ **لا تشارك** ملف `.env` أبداً
- ✅ **غيّر** كلمة مرور الأدمن من `admin123`
- ✅ **استخدم** HTTPS دائماً (مُفعّل تلقائياً على PythonAnywhere)

## 💡 نصائح للخطة المجانية

1. **استخدم Caching** للإجابات المكررة
2. **قلل عدد المفاتيح API** إلى 2-3 مفاتيح فقط
3. **ضع حد للـ Rate Limiting** (مثلاً: 10 أسئلة/يوم للمستخدم)
4. **لا تُفعّل Polling** - استخدم Webhook فقط

---

✨ **الآن مشروعك جاهز على الإنترنت!**

للدعم: راجع [PythonAnywhere Help](https://help.pythonanywhere.com)
