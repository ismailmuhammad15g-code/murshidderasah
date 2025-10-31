@echo off
echo ========================================
echo تثبيت مكتبات البوت
echo ========================================
echo.

echo [1/5] تثبيت المكتبات الأساسية...
pip install python-telegram-bot==20.0
pip install python-dotenv==1.0.0

echo.
echo [2/5] تثبيت Google Generative AI...
pip install google-generativeai

echo.
echo [3/5] تثبيت Telethon...
pip install telethon

echo.
echo [4/5] تثبيت ChromaDB (قد يستغرق وقتاً)...
pip install chromadb --no-build-isolation

echo.
echo [5/5] التحقق من التثبيت...
python -c "import telegram; import google.generativeai; import chromadb; import telethon; print('✅ جميع المكتبات تم تثبيتها بنجاح!')"

echo.
echo ========================================
echo اكتمل التثبيت!
echo ========================================
pause
