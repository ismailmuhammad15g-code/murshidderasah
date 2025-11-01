import sqlite3

conn = sqlite3.connect('school_bot.db')
cursor = conn.cursor()

print("=" * 50)
print("الكتب وملفاتها:")
print("=" * 50)

cursor.execute('''
    SELECT l.id, l.title, l.content_type, lf.local_path, lf.file_id
    FROM library l
    LEFT JOIN library_files lf ON l.id = lf.library_item_id
    WHERE l.approved = 1
''')

for row in cursor.fetchall():
    print(f"\nID: {row[0]}")
    print(f"العنوان: {row[1]}")
    print(f"النوع: {row[2]}")
    print(f"المسار المحلي: {row[3]}")
    print(f"معرف الملف: {row[4]}")
    print("-" * 50)

conn.close()
