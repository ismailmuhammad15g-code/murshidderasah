# 🚀 بوت مرشد الدراسة - النسخة الاحترافية الكاملة

<div dir="rtl">

## 📌 نظرة عامة

هذه هي **النسخة الاحترافية والكاملة** من بوت مرشد الدراسة، المصممة للاستضافة القوية (Azure, AWS, VPS) وليس للسيرفرات المجانية الضعيفة.

### ✨ المميزات الرئيسية

#### 🔥 التقنيات الأساسية
- **ChromaDB**: قاعدة بيانات متجهات احترافية وقابلة للتوسع (ليس FAISS)
- **APScheduler**: جدولة مهام آلية في الخلفية (التحديث كل 5 دقائق + التنظيف اليومي)
- **Flask + Telegram Webhooks**: لتطبيقات الإنتاج عالية الأداء

#### 🎯 الميزات الذكية
1. **🔍 RAG ذكي هجين**: يبحث في منشورات الأدمن (رسمي) + نقاشات الطلاب (سياق)
2. **🔄 التحديث الآلي**: كل 5 دقائق يسحب الرسائل الجديدة تلقائياً
3. **🧹 التنظيف التلقائي**: كل يوم عند 3 فجراً يحذف الرسائل القديمة (+365 يوم)
4. **⚡ 10 مفاتيح API**: نظام دوران (Round Robin) لسرعة 10x في البناء والرد

#### 📡 المصادر المتعددة (V2)
- القناة الرئيسية: `@mahadalazhar`
- جروب الإقامات (اختياري): يمكن إضافته في `.env`
- سهولة إضافة مصادر جديدة في `config.py`

---

## 📂 هيكل المشروع

```
schoolnewsbot2/
├── main.py                    # البوت الرئيسي (Polling) + APScheduler
├── flask_app.py              # تطبيق Flask (Webhook للإنتاج)
├── rebuild_database.py       # بناء قاعدة البيانات الكاملة (10 مفاتيح)
├── quick_build.py            # بناء سريع (للتطوير)
├── vector_store.py           # ChromaDB + البحث الهجين
├── scraper.py                # سحب الرسائل من تليجرام
├── bot_logic.py              # منطق الذكاء الاصطناعي (Gemini)
├── config.py                 # الإعدادات (10 مفاتيح + المصادر المتعددة)
├── database.py               # قاعدة بيانات SQLite (المستخدمين/الكتب)
├── requirements.txt          # المكتبات المطلوبة (ChromaDB + APScheduler)
└── .env                      # المفاتيح السرية (راجع .env.example)
```

---

## 🛠️ التثبيت والإعداد

### 1️⃣ المتطلبات الأساسية

- Python 3.9+
- حساب Google Cloud (للحصول على 10 مفاتيح Gemini API)
- حساب Telegram API (API_ID + API_HASH)
- حساب Bot من @BotFather

### 2️⃣ تثبيت المكتبات

```bash
pip install -r requirements.txt
```

**ملاحظة مهمة**: إذا واجهت خطأ في تثبيت `hnswlib` على Windows، قم بتثبيت **Visual C++ Build Tools** من:
https://visualstudio.microsoft.com/visual-cpp-build-tools/

### 3️⃣ إعداد ملف `.env`

أنشئ ملف `.env` في جذر المشروع:

```env
# === بوت تليجرام ===
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# === تليجرام API (للسحب من القنوات) ===
TELEGRAM_API_ID=YOUR_API_ID
TELEGRAM_API_HASH=YOUR_API_HASH
CHANNEL_USERNAME=mahadalazhar

# === Google API Keys (10 مفاتيح للدوران) ===
GOOGLE_API_KEY_1=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXX
GOOGLE_API_KEY_2=AIzaSyYYYYYYYYYYYYYYYYYYYYYYYYY
GOOGLE_API_KEY_3=AIzaSyZZZZZZZZZZZZZZZZZZZZZZZZZ
GOOGLE_API_KEY_4=AIzaSyAAAAAAAAAAAAAAAAAAAAAAAA
GOOGLE_API_KEY_5=AIzaSyBBBBBBBBBBBBBBBBBBBBBBBBB
GOOGLE_API_KEY_6=AIzaSyCCCCCCCCCCCCCCCCCCCCCCCCC
GOOGLE_API_KEY_7=AIzaSyDDDDDDDDDDDDDDDDDDDDDDDDD
GOOGLE_API_KEY_8=AIzaSyEEEEEEEEEEEEEEEEEEEEEEEEE
GOOGLE_API_KEY_9=AIzaSyFFFFFFFFFFFFFFFFFFFFFFFFF
GOOGLE_API_KEY_10=AIzaSyGGGGGGGGGGGGGGGGGGGGGGGG

# === نماذج Gemini ===
GEMINI_CHAT_MODEL=gemini-1.5-pro-latest
GEMINI_EMBED_MODEL=models/text-embedding-004

# === جروب الإقامات (اختياري) ===
ACCOMMODATIONS_GROUP_ID=         # اتركه فارغاً إذا لم تكن بحاجته

# === الإعدادات الأخرى ===
DAYS_LIMIT=365
DB_PATH=./db
ADMIN_NAME=your_name
ADMIN_EMAIL=your_email@example.com

# === إعدادات Flask (للإنتاج) ===
WEBHOOK_URL=https://your-domain.com/webhook
HOST=0.0.0.0
PORT=8080
```

---

## 🏗️ بناء قاعدة البيانات

### الطريقة الأولى: البناء الكامل (مُوصى بها للإنتاج)

```bash
python rebuild_database.py
```

**المميزات**:
- ✅ يستخدم الـ 10 مفاتيح API بالدوران (سرعة 10x)
- ✅ يسحب من جميع المصادر (القناة + جروب الإقامات)
- ✅ يصنف الرسائل إلى `admin` و `student`
- ✅ يضيف بطاقة `source_tag` لكل رسالة
- ✅ يبني قاعدة ChromaDB كاملة

**الوقت المتوقع**:
- مفتاح واحد: ~4.5 ساعة
- 5 مفاتيح: ~54 دقيقة
- 10 مفاتيح: ~27 دقيقة

### الطريقة الثانية: البناء السريع (للتطوير)

```bash
python quick_build.py
```

---

## 🚀 تشغيل البوت

### وضع Polling (للتطوير)

```bash
python main.py
```

**المميزات**:
- ✅ APScheduler مُفعّل (التحديث كل 5 دقائق + التنظيف اليومي)
- ✅ نظام دوران الـ 10 مفاتيح في الردود
- ✅ RAG ذكي هجين (admin + student)

### وضع Webhook (للإنتاج)

```bash
python flask_app.py
```

**متطلبات Webhook**:
1. دومين بـ HTTPS (مثل: `https://your-domain.com`)
2. إضافة `WEBHOOK_URL` في `.env`
3. تعيين Webhook:
   ```bash
   python set_webhook.py
   ```

---

## 🔧 المهام الآلية (APScheduler)

### 🔍 مهمة 1: الباحث السريع
- **التكرار**: كل 5 دقائق
- **الوظيفة**: سحب الرسائل الجديدة من القناة وإضافتها لقاعدة البيانات
- **الملف**: `main.py` → `scrape_new_messages_job()`

### 🧹 مهمة 2: عامل النظافة
- **التكرار**: يومياً عند 3:00 صباحاً (بتوقيت السعودية)
- **الوظيفة**: حذف الرسائل الأقدم من 365 يوم
- **الملف**: `main.py` → `prune_old_messages_job()`

---

## 🎯 نظام الدوران (Round Robin) - الـ 10 مفاتيح

### في البناء (`rebuild_database.py`)
```python
# يستخدم المفاتيح بالتوالي:
# الدفعة 1 → مفتاح 1
# الدفعة 2 → مفتاح 2
# ...
# الدفعة 11 → مفتاح 1 (دورة جديدة)
```

### في الردود (`main.py`)
```python
# كل مرة يسأل مستخدم، يتم استخدام المفتاح التالي:
# سؤال 1 → مفتاح 1
# سؤال 2 → مفتاح 2
# ...
# سؤال 11 → مفتاح 1 (دورة جديدة)
```

**الفائدة**: تجنب حد Rate Limit (15 طلب/دقيقة لكل مفتاح) → 10 مفاتيح = 150 طلب/دقيقة!

---

## 🔍 البحث الهجين الذكي (RAG V2)

### كيف يعمل؟

1. **يكتشف الكلمات المفتاحية**: إذا كان السؤال عن "إقامة"، يبحث في جروب الإقامات أولاً
2. **يبحث في منشورات الأدمن**: (type='admin') → منشورات رسمية موثوقة
3. **يبحث في نقاشات الطلاب**: (type='student') → سياق إضافي مفيد
4. **يجمع النتائج**: ويرسلها لـ Gemini لتحليلها والرد بشكل ذكي

### مثال:

```
المستخدم: "متى الامتحانات؟"
          ↓
    1. بحث في admin (منشورات الأدمن)
          ↓
    2. بحث في student (نقاشات الطلاب)
          ↓
    3. جمع النتائج
          ↓
    4. Gemini يحلل ويرد: "بناءً على منشور الأدمن في 15 يناير..."
```

---

## 📡 إضافة مصادر جديدة

### في `config.py`:

```python
TELEGRAM_SOURCES = [
    {
        "id": "mahadalazhar",        # القناة الرئيسية
        "tag": "public_channel",
        "type": "public"
    },
    {
        "id": "YOUR_GROUP_ID",       # جروب جديد
        "tag": "accommodations",
        "type": "private"
    },
    {
        "id": "ANOTHER_CHANNEL",     # قناة أخرى
        "tag": "exams",
        "type": "public"
    }
]
```

**ملاحظة**: للجروبات الخاصة، تأكد أن حسابك (anon.session) منضم لها.

---

## 🐛 استكشاف الأخطاء

### خطأ: `hnswlib not found`

**الحل**:
1. ثبّت Visual C++ Build Tools
2. `pip install hnswlib`

### خطأ: `Rate Limit exceeded`

**الحل**: أضف المزيد من المفاتيح في `.env` (حتى 10 مفاتيح)

### خطأ: `0 messages scraped`

**الحل**:
1. تأكد أن حسابك منضم للقنوات/الجروبات
2. احذف ملف `anon.session` وأعد المحاولة

---

## 📊 الإحصائيات

عند التشغيل، ستظهر إحصائيات مثل:

```
✅ تم سحب 12,543 رسالة
   📊 التصنيف:
      • منشورات رسمية (admin): 8,234
      • نقاشات طلاب (student): 4,309
   
   📡 توزيع المصادر:
      • public_channel: 10,000
      • accommodations: 2,543
```

---

## 🚀 نشر البوت على Azure/AWS

### Azure (مُوصى به)

1. أنشئ **Azure App Service**
2. ارفع الكود:
   ```bash
   git push azure main
   ```
3. أضف المتغيرات البيئية في **Configuration** → **Application Settings**
4. شغّل:
   ```bash
   python rebuild_database.py  # مرة واحدة فقط
   python flask_app.py         # التشغيل الدائم
   ```

### AWS (EC2)

1. أنشئ **EC2 instance** (Ubuntu)
2. ثبّت Python 3.9+:
   ```bash
   sudo apt update
   sudo apt install python3.9 python3-pip
   ```
3. انسخ الملفات وثبّت:
   ```bash
   pip3 install -r requirements.txt
   ```
4. شغّل مع **screen** أو **systemd**

---

## 📝 الترخيص

مشروع تعليمي مفتوح المصدر. استخدمه بحرية!

---

## 👨‍💻 المطور

لأي استفسارات أو دعم، تواصل معنا:
- Email: zetsuserv@gmail.com
- Telegram: @mahadalazhar

---

🌟 **شكراً لاستخدامك بوت مرشد الدراسة - النسخة الاحترافية!** 🌟

</div>
