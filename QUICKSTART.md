# ⚡ دليل البداية السريعة

أسرع طريقة لبدء استخدام **بوابة مرشد الدراسة**.

---

## 🚀 في 3 خطوات فقط

### 1️⃣ تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 2️⃣ ضبط المفاتيح في `.env`
افتح ملف `.env` وأضف:
- `BOT_TOKEN` (من @BotFather)
- `GOOGLE_API_KEY_1` (على الأقل مفتاح واحد)
- `FLASK_SECRET_KEY` (أي نص عشوائي)

### 3️⃣ تشغيل المشروع
```bash
python run.py
```

✅ **جاهز!** افتح المتصفح: http://localhost:8080

---

## 🔐 تسجيل الدخول

**الحساب التجريبي:**
- Username: `admin`
- Password: `admin123`

---

## 📋 الأوامر المفيدة

### اختبار الإعداد
```bash
python test_setup.py
```

### إدارة قاعدة البيانات
```bash
python db_manager.py
```
ستحصل على قائمة تفاعلية لإدارة المستخدمين والكتب.

### تشغيل مباشر (بدون فحص)
```bash
python flask_app.py
```

---

## 🌐 النشر على PythonAnywhere

### الطريقة السريعة:

1. ارفع المشروع (Git أو رفع مباشر)
2. في Bash Console:
   ```bash
   cd ~/schoolnewsbot2
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. أنشئ Web App (Flask)
4. عدّل WSGI config حسب `DEPLOYMENT.md`
5. افتح: `https://your-username.pythonanywhere.com/set-webhook`

**التفاصيل الكاملة:** راجع `DEPLOYMENT.md`

---

## 🎯 الميزات الرئيسية

| الميزة | الرابط المحلي |
|--------|--------------|
| الصفحة الرئيسية | http://localhost:8080 |
| المكتبة | http://localhost:8080/library |
| الاستفسار الذكي | http://localhost:8080/smart-query |
| رفع كتاب | http://localhost:8080/upload |

---

## 🐛 حل المشاكل السريع

### المشكلة: "ModuleNotFoundError"
**الحل:**
```bash
pip install [اسم المكتبة]
```

### المشكلة: "BOT_TOKEN not found"
**الحل:** تأكد من وجود `.env` وأنه يحتوي على `BOT_TOKEN=...`

### المشكلة: "Database not found"
**الحل:** تأكد من وجود مجلد `db/` (قاعدة ChromaDB)

### المشكلة: "Port already in use"
**الحل:** غيّر PORT في `.env` (مثلاً: `PORT=5000`)

---

## 💡 نصائح

1. ✅ استخدم `test_setup.py` قبل أول تشغيل
2. ✅ استخدم `db_manager.py` لإضافة كتب تجريبية
3. ✅ جرّب الاستفسار الذكي بأسئلة حقيقية
4. ✅ غيّر كلمة مرور `admin` قبل النشر!

---

## 📚 موارد إضافية

- **التوثيق الكامل:** `README.md`
- **دليل النشر:** `DEPLOYMENT.md`
- **إدارة قاعدة البيانات:** `python db_manager.py`
- **الاختبار:** `python test_setup.py`

---

## 🆘 الدعم

إذا واجهت مشكلة:
1. راجع `DEPLOYMENT.md` للمشاكل الشائعة
2. شغّل `python test_setup.py` للتشخيص
3. تحقق من ملفات Log في Flask

---

**🎉 استمتع باستخدام بوابة مرشد الدراسة!**
