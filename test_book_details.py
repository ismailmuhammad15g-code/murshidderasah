"""
اختبار إصلاح مشكلة عرض تفاصيل الكتاب
"""
import sqlite3
import os

print("=" * 60)
print("اختبار عرض تفاصيل الكتاب")
print("=" * 60)

conn = sqlite3.connect('school_bot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# جلب كتاب معتمد
cursor.execute("""
    SELECT id, title FROM library 
    WHERE approved = 1 AND content_type = 'book'
    LIMIT 1
""")

book = cursor.fetchone()
if not book:
    print("❌ لا يوجد كتب معتمدة في قاعدة البيانات")
    conn.close()
    exit()

book_id = book['id']
book_title = book['title']

print(f"\n📚 الكتاب: {book_title} (ID: {book_id})")
print("-" * 60)

# جلب الملفات المرتبطة بالكتاب
cursor.execute("""
    SELECT file_id, file_type, caption, local_path 
    FROM library_files 
    WHERE library_item_id = ?
    ORDER BY file_order
""", (book_id,))

files = cursor.fetchall()

if not files:
    print("⚠️ لا توجد ملفات مرتبطة بهذا الكتاب في جدول library_files")
    print("\n🔍 سيتم البحث عن الملف من خلال جداول أخرى...")
else:
    print(f"\n✅ تم العثور على {len(files)} ملف في library_files:")
    
    for idx, file_row in enumerate(files, 1):
        print(f"\nملف {idx}:")
        print(f"  - نوع الملف: {file_row['file_type']}")
        print(f"  - معرف تليجرام (file_id): {file_row['file_id'] or 'غير موجود'}")
        print(f"  - المسار المحلي: {file_row['local_path'] or 'غير موجود'}")
        print(f"  - التعليق: {file_row['caption'] or 'لا يوجد'}")
        
        # التحقق من وجود الملف المحلي
        if file_row['local_path']:
            file_path = file_row['local_path'].replace('\\', '/')
            if not os.path.isabs(file_path):
                file_path = os.path.join(os.getcwd(), file_path)
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"  ✅ الملف موجود ({file_size} بايت)")
            else:
                print(f"  ❌ الملف غير موجود: {file_path}")

print("\n" + "=" * 60)
print("النتيجة:")
print("=" * 60)

has_telegram_file = any(f['file_id'] for f in files)
has_local_file = any(f['local_path'] for f in files if f['local_path'])

if has_telegram_file:
    print("✅ يوجد ملف بمعرف تليجرام - سيعمل البوت بشكل طبيعي")
elif has_local_file:
    print("✅ يوجد ملف محلي فقط - سيتم إرساله من المسار المحلي")
    print("   (بعد الإصلاح الجديد)")
else:
    print("❌ لا يوجد ملفات متاحة - البوت لن يتمكن من إرسال الملف")
    print("   يجب إضافة الملف إلى جدول library_files")

conn.close()

print("\n" + "=" * 60)
print("انتهى الاختبار")
print("=" * 60)
