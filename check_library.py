import sqlite3

conn = sqlite3.connect('school_bot.db')
cursor = conn.cursor()

# فحص بنية الجدول
print("=" * 50)
print("بنية جدول library:")
print("=" * 50)
cursor.execute('PRAGMA table_info(library)')
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

print("\n" + "=" * 50)
print("عدد الكتب في قاعدة البيانات:")
print("=" * 50)
cursor.execute('SELECT COUNT(*) FROM library')
total = cursor.fetchone()[0]
print(f"إجمالي العناصر: {total}")

cursor.execute('SELECT COUNT(*) FROM library WHERE approved = 1')
approved = cursor.fetchone()[0]
print(f"العناصر المعتمدة: {approved}")

cursor.execute('SELECT COUNT(*) FROM library WHERE approved = 1 AND content_type = "book"')
books = cursor.fetchone()[0]
print(f"الكتب المعتمدة: {books}")

# عرض بعض الكتب
print("\n" + "=" * 50)
print("عينة من الكتب:")
print("=" * 50)
cursor.execute('''
    SELECT id, title, uploader_name, upload_date, approved, content_type
    FROM library
    LIMIT 5
''')
for row in cursor.fetchall():
    print(f"ID: {row[0]}, العنوان: {row[1]}, الناشر: {row[2]}, التاريخ: {row[3]}, معتمد: {row[4]}, النوع: {row[5]}")

conn.close()
