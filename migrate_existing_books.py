#!/usr/bin/env python3
"""
نقل الكتب الموجودة من التخزين المحلي (static/uploads) إلى Google Drive
يقرأ جميع الكتب من library_files ذات local_path، يرفعها لـ Google Drive، 
ثم يحدث قاعدة البيانات بروابط Google Drive
"""

import sqlite3
import os
import sys
from drive_uploader import upload_book
import time

def migrate_books():
    """نقل جميع الكتب من التخزين المحلي إلى Google Drive"""
    try:
        conn = sqlite3.connect('school_bot.db')
        cursor = conn.cursor()
        
        # الحصول على جميع الكتب التي لها local_path ولا يوجد لها drive_link
        cursor.execute("""
            SELECT id, library_item_id, local_path, file_type 
            FROM library_files 
            WHERE local_path IS NOT NULL 
            AND local_path != ''
            AND (drive_link IS NULL OR drive_link = '')
        """)
        
        books_to_migrate = cursor.fetchall()
        
        if not books_to_migrate:
            print("✅ لا توجد كتب للهجرة!")
            conn.close()
            return
        
        print(f"📚 تم العثور على {len(books_to_migrate)} كتاب للهجرة...")
        
        success_count = 0
        fail_count = 0
        
        for row in books_to_migrate:
            file_id, library_item_id, local_path, file_type = row
            
            # التحقق من وجود الملف
            if not os.path.exists(local_path):
                print(f"⚠️ ملف غير موجود: {local_path} (ID: {file_id})")
                fail_count += 1
                continue
            
            # الحصول على اسم الكتاب
            cursor.execute("SELECT title FROM library WHERE id = ?", (library_item_id,))
            book_info = cursor.fetchone()
            book_title = book_info[0] if book_info else "Unknown"
            
            print(f"\n⏳ [{success_count + fail_count + 1}/{len(books_to_migrate)}] جارِ رفع: {book_title}")
            print(f"   المسار المحلي: {local_path}")
            
            try:
                # رفع إلى Google Drive
                drive_link = upload_book(local_path)
                
                if drive_link:
                    # تحديث قاعدة البيانات
                    cursor.execute("""
                        UPDATE library_files 
                        SET drive_link = ? 
                        WHERE id = ?
                    """, (drive_link, file_id))
                    
                    # تحديث file_id في جدول library
                    file_id_from_drive = drive_link.split('/d/')[1].split('/')[0] if '/d/' in drive_link else drive_link
                    cursor.execute("""
                        UPDATE library 
                        SET file_id = ? 
                        WHERE id = ?
                    """, (file_id_from_drive, library_item_id))
                    
                    conn.commit()
                    print(f"✅ تم بنجاح: {book_title}")
                    print(f"   رابط Drive: {drive_link}")
                    success_count += 1
                    
                    # إزالة الملف المحلي بعد النقل الناجح (اختياري)
                    # إذا أردت حذف الملفات المحلية بعد النقل، أزل التعليق عن السطور التالية:
                    # os.remove(local_path)
                    # print(f"   🗑️ تم حذف الملف المحلي")
                    
                else:
                    print(f"❌ فشل رفع: {book_title}")
                    fail_count += 1
                
                # تأخير بسيط لتجنب Rate Limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ خطأ في رفع {book_title}: {e}")
                fail_count += 1
        
        conn.close()
        
        print("\n" + "="*60)
        print(f"✅ اكتملت الهجرة!")
        print(f"   نجح: {success_count}")
        print(f"   فشل: {fail_count}")
        print(f"   الإجمالي: {len(books_to_migrate)}")
        print("="*60)
        
        if fail_count > 0:
            print("\n⚠️ تحذير: بعض الكتب فشل رفعها. راجع الأخطاء أعلاه.")
            
    except Exception as e:
        print(f"❌ خطأ عام: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("="*60)
    print("📦 نقل الكتب من التخزين المحلي إلى Google Drive")
    print("="*60)
    
    response = input("\n⚠️ هل تريد المتابعة؟ (y/n): ")
    if response.lower() != 'y':
        print("❌ تم الإلغاء.")
        sys.exit(0)
    
    migrate_books()
