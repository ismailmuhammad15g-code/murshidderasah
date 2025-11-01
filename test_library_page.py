"""
سكريبت اختبار لصفحة المكتبة
"""
import sqlite3
from datetime import datetime

print("=" * 60)
print("اختبار صفحة المكتبة")
print("=" * 60)

# الاتصال بقاعدة البيانات
conn = sqlite3.connect('school_bot.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# جلب الكتب تماماً كما في flask_app.py
cursor.execute("""
    SELECT id, title, description, category, uploader_name, uploader_id,
           upload_date, downloads, views, content_type
    FROM library 
    WHERE approved = 1 AND content_type = 'book'
    ORDER BY upload_date DESC
""")

books = []
for row in cursor.fetchall():
    # تحويل التاريخ
    upload_datetime = datetime.now()
    if row['upload_date']:
        try:
            upload_date_str = row['upload_date']
            if 'T' in upload_date_str:
                upload_datetime = datetime.fromisoformat(upload_date_str.split('.')[0])
            else:
                upload_datetime = datetime.strptime(upload_date_str, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f"⚠️ خطأ في تحليل التاريخ: {e}")
            upload_datetime = datetime.now()
    
    book_data = {
        'id': row['id'],
        'title': row['title'],
        'description': row['description'] or 'لا يوجد وصف',
        'category': row['category'] or 'عام',
        'author': row['uploader_name'] or 'غير معروف',
        'uploaded_by': row['uploader_id'],
        'uploaded_at': upload_datetime,
        'downloads': row['downloads'] or 0,
        'views': row['views'] or 0
    }
    books.append(book_data)

print(f"\n✅ تم العثور على {len(books)} كتاب معتمد")
print("\nتفاصيل الكتب:")
print("-" * 60)

for book in books:
    print(f"\nID: {book['id']}")
    print(f"العنوان: {book['title']}")
    print(f"الوصف: {book['description'][:50]}...")
    print(f"التصنيف: {book['category']}")
    print(f"الناشر: {book['author']}")
    print(f"تاريخ النشر: {book['uploaded_at'].strftime('%Y-%m-%d')}")
    print(f"التحميلات: {book['downloads']}")
    print(f"المشاهدات: {book['views']}")
    
    # التحقق من وجود الملف
    cursor.execute("""
        SELECT local_path FROM library_files WHERE library_item_id = ?
    """, (book['id'],))
    file_result = cursor.fetchone()
    
    if file_result and file_result['local_path']:
        import os
        file_path = file_result['local_path'].replace('\\', '/')
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)
        
        if os.path.exists(file_path):
            print(f"✅ الملف موجود: {file_path}")
        else:
            print(f"❌ الملف غير موجود: {file_path}")
    else:
        print("❌ لا يوجد ملف مرتبط بهذا الكتاب")
    
    print("-" * 60)

conn.close()

print("\n" + "=" * 60)
print("انتهى الاختبار")
print("=" * 60)
