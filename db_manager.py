#!/usr/bin/env python3
# db_manager.py
"""
أداة إدارة قاعدة البيانات - إنشاء، حذف، إعادة ضبط
"""

import sys
import os
from flask_app import app
from models import db, User, Book

def create_tables():
    """إنشاء جداول قاعدة البيانات"""
    print("🔨 جاري إنشاء الجداول...")
    with app.app_context():
        db.create_all()
    print("✅ تم إنشاء الجداول بنجاح!")

def drop_tables():
    """حذف جميع الجداول"""
    print("⚠️  جاري حذف جميع الجداول...")
    with app.app_context():
        db.drop_all()
    print("✅ تم حذف الجداول بنجاح!")

def reset_database():
    """إعادة ضبط قاعدة البيانات (حذف وإعادة إنشاء)"""
    print("🔄 جاري إعادة ضبط قاعدة البيانات...")
    drop_tables()
    create_tables()
    create_admin_user()
    print("✅ تمت إعادة ضبط قاعدة البيانات!")

def create_admin_user():
    """إنشاء مستخدم أدمن"""
    with app.app_context():
        # التحقق من وجود الأدمن
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print("⚠️  مستخدم admin موجود بالفعل")
            return
        
        # إنشاء أدمن جديد
        admin = User(username='admin', name='المسؤول', email='admin@example.com')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✅ تم إنشاء مستخدم admin بكلمة مرور: admin123")

def show_stats():
    """عرض إحصائيات قاعدة البيانات"""
    print("\n📊 إحصائيات قاعدة البيانات:")
    print("=" * 50)
    
    with app.app_context():
        users = User.query.all()
        books = Book.query.all()
        
        print(f"👥 عدد المستخدمين: {len(users)}")
        if users:
            print("\n📋 قائمة المستخدمين:")
            for user in users:
                print(f"  • {user.username} ({user.name or 'بدون اسم'}) - {user.email or 'بدون بريد'}")
        
        print(f"\n📚 عدد الكتب: {len(books)}")
        if books:
            print("\n📋 قائمة الكتب:")
            for book in books:
                print(f"  • {book.title} - {book.author or 'مؤلف غير معروف'}")
                print(f"    التحميلات: {book.downloads} | الحجم: {book.file_size / 1024 / 1024:.2f} MB")
    
    print("=" * 50)

def add_sample_books():
    """إضافة كتب تجريبية"""
    print("📚 جاري إضافة كتب تجريبية...")
    
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("❌ يجب إنشاء مستخدم admin أولاً")
            return
        
        sample_books = [
            {
                'title': 'النحو الواضح - الجزء الأول',
                'author': 'علي الجارم ومصطفى أمين',
                'description': 'كتاب في قواعد اللغة العربية للمرحلة الابتدائية'
            },
            {
                'title': 'التفسير الميسر',
                'author': 'مجموعة من العلماء',
                'description': 'تفسير موجز لمعاني القرآن الكريم'
            },
            {
                'title': 'الفقه الميسر',
                'author': 'د. محمد الزحيلي',
                'description': 'كتاب مبسط في الفقه الإسلامي'
            }
        ]
        
        for book_data in sample_books:
            # التحقق من عدم وجود الكتاب
            existing = Book.query.filter_by(title=book_data['title']).first()
            if existing:
                print(f"  ⚠️  {book_data['title']} موجود بالفعل")
                continue
            
            book = Book(
                title=book_data['title'],
                author=book_data['author'],
                description=book_data['description'],
                filename=f"{book_data['title'].replace(' ', '_')}.pdf",
                file_path=f"static/uploads/{book_data['title'].replace(' ', '_')}.pdf",
                file_size=0,  # حجم وهمي
                uploaded_by=admin.id
            )
            db.session.add(book)
            print(f"  ✅ تمت إضافة: {book_data['title']}")
        
        db.session.commit()
    
    print("✅ تمت إضافة الكتب التجريبية!")

def show_menu():
    """عرض قائمة الخيارات"""
    print("\n" + "=" * 60)
    print("🗄️  أداة إدارة قاعدة البيانات")
    print("=" * 60)
    print("1. إنشاء الجداول")
    print("2. حذف الجداول")
    print("3. إعادة ضبط قاعدة البيانات (حذف + إنشاء)")
    print("4. إنشاء مستخدم admin")
    print("5. عرض الإحصائيات")
    print("6. إضافة كتب تجريبية")
    print("0. خروج")
    print("=" * 60)

def main():
    """الدالة الرئيسية"""
    
    while True:
        show_menu()
        choice = input("\n🔢 اختر رقماً: ").strip()
        
        if choice == '1':
            create_tables()
        elif choice == '2':
            confirm = input("⚠️  هل أنت متأكد من حذف جميع الجداول؟ (yes/no): ")
            if confirm.lower() == 'yes':
                drop_tables()
            else:
                print("❌ تم الإلغاء")
        elif choice == '3':
            confirm = input("⚠️  هل أنت متأكد من إعادة ضبط قاعدة البيانات؟ (yes/no): ")
            if confirm.lower() == 'yes':
                reset_database()
            else:
                print("❌ تم الإلغاء")
        elif choice == '4':
            create_admin_user()
        elif choice == '5':
            show_stats()
        elif choice == '6':
            add_sample_books()
        elif choice == '0':
            print("\n👋 إلى اللقاء!")
            break
        else:
            print("❌ اختيار غير صحيح!")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 تم إيقاف البرنامج")
        sys.exit(0)
