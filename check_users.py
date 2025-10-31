import sqlite3

conn = sqlite3.connect('school_bot.db')
c = conn.cursor()

# Check table structure
c.execute("PRAGMA table_info(users)")
columns = c.fetchall()
print('أعمدة جدول users:')
for col in columns:
    print(f'  {col[1]} ({col[2]})')

print('\n' + '='*50 + '\n')

c.execute('SELECT user_id, name FROM users')
users = c.fetchall()

print(f'إجمالي المستخدمين: {len(users)}')
print('\nقائمة المستخدمين:')
for u in users:
    print(f'  ID: {u[0]}, الاسم: {u[1]}')

conn.close()
