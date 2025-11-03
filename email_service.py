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


def send_verification_email(email: str, name: str, verification_token: str) -> bool:
    """
    إرسال رابط التحقق للمستخدم الجديد
    
    Args:
        email: إيميل المستخدم
        name: اسم المستخدم
        verification_token: رمز التحقق
        
    Returns:
        bool: True إذا نجح الإرسال، False إذا فشل
    """
    try:
        # بناء رابط التفعيل (استخدام WEBSITE_URL من Config)
        base_url = Config.WEBSITE_URL.rstrip('/')
        verification_url = f"{base_url}/verify-email?token={verification_token}"
        
        # إنشاء الرسالة
        msg = MIMEMultipart('alternative')
        msg['From'] = Config.MAIL_DEFAULT_SENDER
        msg['To'] = email
        msg['Subject'] = 'تفعيل حسابك - مرشد الدراسة'
        
        # محتوى الرسالة (HTML جميل)
        html_body = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .welcome {{
                    font-size: 20px;
                    color: #333;
                    margin-bottom: 20px;
                }}
                .message {{
                    color: #666;
                    line-height: 1.8;
                    margin-bottom: 30px;
                }}
                .btn {{
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    padding: 15px 40px;
                    border-radius: 5px;
                    font-size: 16px;
                    font-weight: bold;
                    text-align: center;
                }}
                .btn:hover {{
                    opacity: 0.9;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #999;
                    font-size: 12px;
                }}
                .note {{
                    background-color: #fff3cd;
                    border-right: 4px solid #ffc107;
                    padding: 15px;
                    margin-top: 20px;
                    border-radius: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎓 مرحباً بك في مرشد الدراسة</h1>
                </div>
                
                <div class="content">
                    <div class="welcome">
                        مرحباً {name} 👋
                    </div>
                    
                    <div class="message">
                        <p>شكراً لتسجيلك في منصة <strong>مرشد الدراسة</strong>!</p>
                        <p>لإكمال عملية التسجيل، الرجاء الضغط على الزر أدناه لتفعيل حسابك:</p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verification_url}" class="btn">
                            ✅ تفعيل الحساب الآن
                        </a>
                    </div>
                    
                    <div class="note">
                        <strong>⚠️ ملاحظة:</strong> رابط التفعيل صالح لمدة 24 ساعة فقط.
                    </div>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 14px;">
                        <p>إذا لم تقم بالتسجيل، يمكنك تجاهل هذه الرسالة.</p>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© 2025 مرشد الدراسة - جميع الحقوق محفوظة</p>
                    <p>📧 {Config.MAIL_DEFAULT_SENDER}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # نص بديل بسيط
        text_body = f"""
        مرحباً {name}!
        
        شكراً لتسجيلك في مرشد الدراسة.
        
        لتفعيل حسابك، اضغط على الرابط التالي:
        {verification_url}
        
        رابط التفعيل صالح لمدة 24 ساعة.
        
        مع تحيات فريق مرشد الدراسة
        """
        
        msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # إرسال الإيميل
        with smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT) as server:
            if Config.MAIL_USE_TLS:
                server.starttls()
            
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ تم إرسال إيميل التحقق إلى: {email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل إرسال إيميل التحقق: {e}")
        return False
