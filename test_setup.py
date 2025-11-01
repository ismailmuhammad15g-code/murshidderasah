#!/usr/bin/env python3
# test_setup.py
"""
سكريبت سريع لاختبار إعداد المشروع
"""

import sys
import os

def test_imports():
    """اختبار استيراد المكتبات الأساسية"""
    print("🔍 اختبار المكتبات...")
    
    try:
        import flask
        print("  ✅ Flask:", flask.__version__)
    except ImportError as e:
        print(f"  ❌ Flask: {e}")
        return False
    
    try:
        import flask_sqlalchemy
        print("  ✅ Flask-SQLAlchemy")
    except ImportError as e:
        print(f"  ❌ Flask-SQLAlchemy: {e}")
        return False
    
    try:
        import flask_login
        print("  ✅ Flask-Login")
    except ImportError as e:
        print(f"  ❌ Flask-Login: {e}")
        return False
    
    try:
        import telegram
        print("  ✅ python-telegram-bot:", telegram.__version__)
    except ImportError as e:
        print(f"  ❌ python-telegram-bot: {e}")
        return False
    
    try:
        import google.generativeai as genai
        print("  ✅ google-generativeai")
    except ImportError as e:
        print(f"  ❌ google-generativeai: {e}")
        return False
    
    try:
        import chromadb
        print("  ✅ ChromaDB:", chromadb.__version__)
    except ImportError as e:
        print(f"  ❌ ChromaDB: {e}")
        return False
    
    return True


def test_files():
    """اختبار وجود الملفات الأساسية"""
    print("\n📂 اختبار الملفات...")
    
    required_files = [
        'flask_app.py',
        'bot_logic.py',
        'models.py',
        'config.py',
        'vector_store.py',
        '.env',
        'requirements.txt'
    ]
    
    all_exist = True
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - غير موجود!")
            all_exist = False
    
    return all_exist


def test_directories():
    """اختبار وجود المجلدات"""
    print("\n📁 اختبار المجلدات...")
    
    required_dirs = [
        'templates',
        'static/uploads',
        'db'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ⚠️  {dir_path}/ - غير موجود!")
            if dir_path != 'db':  # db قد لا يكون موجوداً في البداية
                all_exist = False
    
    return all_exist


def test_env():
    """اختبار ملف .env"""
    print("\n🔑 اختبار المتغيرات البيئية...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'BOT_TOKEN',
        'GOOGLE_API_KEY_1',
        'FLASK_SECRET_KEY'
    ]
    
    all_set = True
    for var in required_vars:
        value = os.getenv(var)
        if value and value not in ['your_', 'change-this']:
            print(f"  ✅ {var}: مضبوط")
        else:
            print(f"  ⚠️  {var}: غير مضبوط أو قيمة افتراضية")
            all_set = False
    
    return all_set


def test_database():
    """اختبار قاعدة البيانات"""
    print("\n🗄️  اختبار قاعدة البيانات...")
    
    try:
        from flask_app import app
        with app.app_context():
            from models import db, User, Book
            
            # التحقق من إنشاء الجداول
            users = User.query.count()
            books = Book.query.count()
            
            print(f"  ✅ قاعدة البيانات تعمل")
            print(f"  📊 عدد المستخدمين: {users}")
            print(f"  📚 عدد الكتب: {books}")
            return True
    except Exception as e:
        print(f"  ❌ خطأ في قاعدة البيانات: {e}")
        return False


def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("🧪 اختبار إعداد مشروع 'بوابة مرشد الدراسة'")
    print("=" * 60)
    
    results = []
    
    # الاختبارات
    results.append(("المكتبات", test_imports()))
    results.append(("الملفات", test_files()))
    results.append(("المجلدات", test_directories()))
    results.append(("المتغيرات البيئية", test_env()))
    results.append(("قاعدة البيانات", test_database()))
    
    # النتيجة النهائية
    print("\n" + "=" * 60)
    print("📊 ملخص النتائج:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ نجح" if passed else "❌ فشل"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 رائع! جميع الاختبارات نجحت!")
        print("🚀 يمكنك الآن تشغيل المشروع بـ: python flask_app.py")
    else:
        print("⚠️  بعض الاختبارات فشلت. راجع الأخطاء أعلاه.")
        print("💡 نصيحة: راجع ملف DEPLOYMENT.md للتفاصيل")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
