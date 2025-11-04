import os
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import Config  # يفترض أن هذا يقرأ المتغيرات

logger = logging.getLogger(__name__)

# --- الإعدادات الأساسية ---
# اسم الملف السري المحلي
LOCAL_SERVICE_ACCOUNT_FILE = 'murshidderasah-950af6007108.json'
# معرف المجلد في جوجل درايف
TARGET_FOLDER_ID = '1zmf3UO6dZDQrlHptZuyMUide-EQGHBSH'
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """
    يقوم بتسجيل الدخول بذكاء:
    1. يبحث عن متغير البيئة (للإنتاج)
    2. إذا فشل، يبحث عن الملف المحلي (للتطوير)
    """
    creds = None
    
    # 1. محاولة القراءة من متغيرات البيئة (للإنتاج)
    service_account_json_string = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if service_account_json_string:
        try:
            service_account_info = json.loads(service_account_json_string)
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES)
            logger.info("✅ (Drive) تم تسجيل الدخول باستخدام متغير البيئة.")
        except Exception as e:
            logger.error(f"❌ (Drive) فشل في قراءة متغير البيئة: {e}")
            return None
    
    # 2. إذا فشلت المحاولة الأولى، ابحث عن الملف المحلي (للتطوير)
    if not creds:
        try:
            creds = service_account.Credentials.from_service_account_file(
                LOCAL_SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            logger.info(f"✅ (Drive) تم تسجيل الدخول باستخدام الملف المحلي: {LOCAL_SERVICE_ACCOUNT_FILE}")
        except FileNotFoundError:
            logger.error(f"❌ (Drive) خطأ فادح: لم يتم العثور على متغير البيئة ولا الملف المحلي '{LOCAL_SERVICE_ACCOUNT_FILE}'")
            return None
        except Exception as e:
            logger.error(f"❌ (Drive) خطأ في قراءة الملف المحلي: {e}")
            return None
            
    # بناء خدمة الـ API
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_book(file_path: str):
    """
    دالة لرفع ملف إلى مجلد جوجل درايف
    وترجع رابط الملف المرفوع
    """
    service = get_drive_service()
    if not service:
        logger.error("❌ (Drive) لا يمكن الرفع، الخدمة غير متصلة.")
        return None

    file_name = os.path.basename(file_path)
    file_metadata = {'name': file_name, 'parents': [TARGET_FOLDER_ID]}
    media = MediaFileUpload(file_path, resumable=True)
    
    try:
        logger.info(f"⏳ (Drive) جاري رفع الملف: {file_name}...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        file_id = file.get('id')
        link = file.get('webViewLink')
        
        # جعل الملف قابلاً للقراءة (عام)
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        
        logger.info(f"✅ (Drive) تم الرفع بنجاح! الرابط: {link}")
        return link

    except Exception as e:
        logger.error(f"❌ (Drive) حدث خطأ أثناء الرفع: {e}")
        return None
