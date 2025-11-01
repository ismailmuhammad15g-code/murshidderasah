# إصلاح مشكلة Timeout عند رفع الملفات الكبيرة

## المشكلة
```
❌ خطأ في إرسال الملف المحلي: Timed out
```

عند محاولة إرسال ملف كبير (3.7 MB) من المسار المحلي، كان الرفع يستغرق وقتاً طويلاً ويتجاوز المهلة الزمنية الافتراضية.

## الحلول المنفذة

### 1️⃣ زيادة وقت الانتهاء (Timeout) للتطبيق
**الملف**: `main.py`

تم إضافة إعدادات `HTTPXRequest` مخصصة:
```python
from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=8,
    connect_timeout=30.0,      # 30 ثانية للاتصال
    read_timeout=60.0,         # 60 ثانية للقراءة  
    write_timeout=120.0,       # 120 ثانية للكتابة (رفع الملفات)
    pool_timeout=30.0
)

application = Application.builder() \
    .token(Config.BOT_TOKEN) \
    .request(request) \
    .build()
```

### 2️⃣ إضافة Timeout مخصص لكل طلب إرسال
**الملف**: `advanced_features.py`

تم إضافة `read_timeout` و `write_timeout` لكل عملية `send_document`:
```python
await context.bot.send_document(
    chat_id=query.from_user.id,
    document=f,
    caption=caption,
    filename=os.path.basename(file_path),
    read_timeout=120,   # 2 دقيقة
    write_timeout=120   # 2 دقيقة
)
```

### 3️⃣ إضافة رسائل تحذيرية للمستخدم
عند رفع ملفات أكبر من 1 MB، يتم إرسال رسالة:
```
⏳ جاري رفع الملفات... (3.7 MB)
قد يستغرق الأمر بعض الوقت، يرجى الانتظار...
```

### 4️⃣ معالجة أخطاء Timeout بشكل أفضل
```python
try:
    # رفع الملف
except asyncio.TimeoutError:
    await context.bot.send_message(
        text="⏱️ عذراً، انتهت مهلة رفع الملف.\n"
             "الملف كبير جداً. يرجى المحاولة لاحقاً."
    )
except Exception as e:
    # معالجة أخطاء أخرى
```

### 5️⃣ التحقق من حجم الملف
- الحد الأقصى لـ Telegram: **50 MB**
- إذا كان الملف أكبر، يتم إرسال رسالة خطأ بدلاً من المحاولة

### 6️⃣ حساب الحجم الكلي للملفات
قبل بدء الرفع، يتم حساب الحجم الكلي وإعلام المستخدم:
```python
total_size = 0
for file_id, file_type, caption, local_path in files:
    if not file_id and local_path:
        # حساب حجم الملف
        if os.path.exists(file_path):
            total_size += os.path.getsize(file_path)

if total_size > 1024 * 1024:  # أكبر من 1 MB
    # إرسال تحذير
```

## الملفات المعدلة
1. ✅ `main.py` - إعدادات HTTPXRequest
2. ✅ `advanced_features.py` - دالتي `show_gallery_handler` و `download_all_files_handler`

## النتيجة المتوقعة
✅ **الملفات حتى 50 MB ستُرفع بنجاح**
✅ **رسائل تحذيرية واضحة للمستخدم**
✅ **معالجة أفضل لأخطاء Timeout**
✅ **تجربة مستخدم محسّنة**

## ملاحظات مهمة

### للملفات الكبيرة جداً (> 10 MB):
يُنصح بحفظ `file_id` بعد أول رفع ناجح:
```python
# بعد الرفع الناجح
sent_message = await context.bot.send_document(...)
file_id = sent_message.document.file_id

# حفظ file_id في قاعدة البيانات
update_library_file_id(book_id, file_id)
```

### للأداء الأفضل:
- استخدام CDN أو خدمة تخزين سحابية للملفات الكبيرة
- ضغط الملفات قبل الرفع
- تقسيم الملفات الكبيرة إلى أجزاء أصغر

## للاختبار
```bash
# إعادة تشغيل البوت
python main.py
```

ثم:
1. افتح البوت في التليجرام
2. اختر كتاب
3. اضغط "عرض المعرض" أو "تحميل جميع الملفات"
4. انتظر الرسالة التحذيرية
5. سيتم رفع الملف بنجاح (قد يستغرق 30-60 ثانية للملفات الكبيرة)
