#!/usr/bin/env python3
"""
إضافة عمود drive_link إلى جدول library_files
لتخزين روابط Google Drive بدلاً من المسارات المحلية فقط
"""

import sqlite3
import sys

def add_drive_link_column():
    try:
        conn = sqlite3.connect('school_bot.db')
        cursor = conn.cursor()
        
        # التحقق من وجود العمود
        cursor.execute("PRAGMA table_info(library_files)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'drive_link' in columns:
            print("✅ عمود drive_link موجود بالفعل!")
            conn.close()
            return
        
        # إضافة العمود
        print("⏳ جارِ إضافة عمود drive_link...")
        cursor.execute("""
            ALTER TABLE library_files 
            ADD COLUMN drive_link TEXT
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ تم إضافة عمود drive_link بنجاح!")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")
        sys.exit(1)

if __name__ == "__main__":
    add_drive_link_column()
