#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
اختبار منطق الدوران (بدون سحب رسائل فعلية)
"""

from config import Config

num_keys = len(Config.GOOGLE_API_KEYS)
print(f"🔥 عدد المفاتيح: {num_keys}")
print()
print("📊 محاكاة الدوران:")
print("="*60)

for batch_num in range(1, 31):  # محاكاة 30 دفعة
    will_wait = (batch_num % num_keys == 0) and (batch_num < 30)
    
    key_num = ((batch_num - 1) % num_keys) + 1
    
    if will_wait:
        print(f"دفعة {batch_num:3d} → مفتاح {key_num:2d} → ⏳ انتظار 65 ثانية (دورة كاملة)")
    else:
        print(f"دفعة {batch_num:3d} → مفتاح {key_num:2d} → ⚡ مباشرة (بدون انتظار)")

print()
print("="*60)
print(f"✅ مع {num_keys} مفاتيح، نوفر {num_keys-1} من كل {num_keys} انتظارات!")
print(f"⚡ السرعة الفعلية: ~{num_keys}x")
