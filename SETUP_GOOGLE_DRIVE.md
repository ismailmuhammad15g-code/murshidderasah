# 🔐 إعداد Google Drive - خطوات مهمة جداً

## ⚠️ خطأ شائع: `storageQuotaExceeded`

إذا رأيت هذا الخطأ:
```
Service Accounts do not have storage quota
```

**السبب:** المجلد `1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH` غير مشارك مع الـ Service Account.

---

## ✅ الحل: مشاركة المجلد مع Service Account

### 1️⃣ افتح المجلد في Google Drive

اذهب إلى: https://drive.google.com/drive/folders/1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH

### 2️⃣ اضغط على "مشاركة" (Share)

في الزاوية اليمنى العليا

### 3️⃣ أضف البريد الإلكتروني للـ Service Account

أضف البريد التالي:

```
murshidderasah@murshidderasah.iam.gserviceaccount.com
```

### 4️⃣ امنحه صلاحية "محرر" (Editor)

**مهم:** اختر "محرر" وليس "عارض" لأن البوت يحتاج رفع ملفات.

### 5️⃣ اضغط "إرسال" (Send)

⚠️ **ملاحظة:** قد تظهر رسالة "لا يمكن إرسال إشعار بالبريد الإلكتروني" - تجاهلها واضغط "متابعة".

---

## 🧪 اختبار الإعداد

بعد المشاركة، جرب:

```bash
python -c "from drive_uploader import upload_book; print(upload_book('test.txt'))"
```

**يجب أن ترى:** رابط Google Drive مثل `https://drive.google.com/file/d/1ABC...XYZ/view`

---

## 📋 معلومات Service Account

- **البريد الإلكتروني:** `murshidderasah@murshidderasah.iam.gserviceaccount.com`
- **Project:** `murshidderasah`
- **المجلد المستهدف:** `1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH`

---

## 🎯 خطوات إضافية (اختيارية)

### إنشاء Shared Drive (بدلاً من المجلد العادي)

إذا كنت تستخدم Google Workspace:

1. اذهب إلى Google Drive
2. اختر "Shared drives" من القائمة الجانبية
3. اضغط "+ New"
4. أضف Service Account كعضو

**ميزة Shared Drive:**
- لا حدود للتخزين على Service Account
- إدارة أفضل للصلاحيات
- لا يتأثر بحذف المستخدمين

---

## 🐛 استكشاف الأخطاء

### خطأ: `403 Forbidden`

```
{'reason': 'forbidden'}
```

**الحل:** تأكد من مشاركة المجلد مع Service Account.

### خطأ: `404 Not Found`

```
{'reason': 'notFound'}
```

**الحل:** 
- تحقق من صحة `TARGET_FOLDER_ID` في `drive_uploader.py`
- تحقق من أن المجلد موجود

### خطأ: `storageQuotaExceeded`

**الحل:** شارك المجلد كما هو موضح أعلاه.

---

## ✅ Checklist

- [ ] مشاركة المجلد `1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH` مع Service Account
- [ ] منح صلاحية "محرر" (Editor)
- [ ] اختبار رفع ملف
- [ ] التحقق من ظهور الملف في Google Drive
- [ ] التحقق من إمكانية الوصول للرابط المُرجع

---

**تاريخ:** 2024
**الحالة:** ✅ مهم جداً - يجب تنفيذ هذه الخطوات
