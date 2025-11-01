#!/usr/bin/env python3
# run.py
"""
سكريبت تشغيل سريع - يستدعي main.py
للتوافق مع الأمر: python run.py أو python main.py
"""

import sys
import os

# إضافة المسار الحالي
sys.path.insert(0, os.path.dirname(__file__))

# استيراد وتشغيل main
from main import main

if __name__ == '__main__':
    main()
