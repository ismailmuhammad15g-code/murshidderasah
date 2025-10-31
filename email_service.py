import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import Config
import logging

logger = logging.getLogger(__name__)

def send_inquiry_email(user_id: int, user_name: str, inquiry_text: str) -> bool:
    """
    إرسال استفسار المستخدم عبر البريد الإلكتروني
    
    Args:
        user_id: معرف المستخدم في تليجرام
        user_name: اسم المستخدم
        inquiry_text: نص الاستفسار
        
    Returns:
        bool: True إذا نجح الإرسال، False إذا فشل
    """
    try:
        # إنشاء الرسالة
        msg = MIMEMultipart()
        msg['From'] = Config.MAIL_DEFAULT_SENDER
        msg['To'] = Config.MAIL_USERNAME
        msg['Subject'] = f'استفسار جديد من البوت - {user_name}'
        
        # محتوى الرسالة
        body = f"""
        ╔═══════════════════════════════════╗
        ║     📩 استفسار جديد من البوت     ║
        ╚═══════════════════════════════════╝
        
        👤 اسم المستخدم: {user_name}
        🆔 معرف المستخدم: {user_id}
        
        📝 الاستفسار:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        {inquiry_text}
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        💡 للرد على هذا الاستفسار:
        استخدم الأمر في البوت:
        /reply {user_id} [رسالتك]
        
        مثال:
        /reply {user_id} شكراً على استفسارك، الإجابة هي...
        
        ═══════════════════════════════════════
        📧 هذه رسالة تلقائية من بوت مدرسة الأزهر
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # الاتصال بخادم SMTP وإرسال الرسالة
        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            if Config.MAIL_USE_TLS:
                server.starttls()
            
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"تم إرسال استفسار {user_id} عبر البريد الإلكتروني بنجاح")
        return True
        
    except Exception as e:
        logger.error(f"فشل إرسال البريد الإلكتروني: {e}")
        return False
