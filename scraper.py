# scraper.py
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from datetime import datetime, timedelta, timezone
import logging
from config import Config

logging.basicConfig(level=logging.INFO)

async def scrape_channel():
    """سحب الرسائل من قناة تليجرام الرسمية"""
    logging.info("بدء عملية سحب الرسائل...")
    
    client = TelegramClient('anon', Config.TELEGRAM_API_ID, Config.TELEGRAM_API_HASH)
    documents = []
    
    try:
        await client.start()
        logging.info("تم الاتصال بـ Telethon.")
        
        channel = await client.get_entity(Config.CHANNEL_USERNAME)
        # محاولة الانضمام للقناة تلقائياً إن لم يكن الحساب منضمّاً
        try:
            await client(JoinChannelRequest(channel))
            logging.info("تم الانضمام للقناة تلقائياً.")
        except Exception:
            pass  # ربما منضم مسبقاً أو قناة عامة

        since_date = datetime.now(timezone.utc) - timedelta(days=Config.DAYS_LIMIT)
        
        message_count = 0
        # اجلب من الأحدث للأقدم وتوقف عند تجاوز الحد الزمني
        async for message in client.iter_messages(channel):
            if message.date and message.date < since_date:
                break
            if message.text:
                # 🏷️ تحديد نوع الرسالة: أدمن (منشور أصلي) أم طالب (رد/محول)
                doc_type = 'admin'  # الافتراضي: منشور رسمي
                
                # إذا كانت الرسالة رداً أو محولة، فهي تعليق طالب
                if message.is_reply or message.fwd_from:
                    doc_type = 'student'
                
                documents.append({
                    "id": f"{channel.id}_{message.id}",
                    "text": message.text,
                    "date": message.date.isoformat() if message.date else "",
                    "link": f"https://t.me/{Config.CHANNEL_USERNAME}/{message.id}",
                    "type": doc_type  # 🏷️ البطاقة الجديدة
                })
                message_count += 1

        logging.info(f"اكتمل السحب. تم تجميع {message_count} رسالة.")
        return documents

    except Exception as e:
        logging.error(f"حدث خطأ أثناء سحب الرسائل: {e}")
        return None  # إرجاع None عند الفشل
    finally:
        await client.disconnect()


async def scrape_recent_messages(minutes: int = 10):
    """
    سحب الرسائل الحديثة فقط من القناة (مخصص للتحديث الآلي)
    
    Args:
        minutes: عدد الدقائق للرجوع للوراء (افتراضي 10 دقائق)
    
    Returns:
        قائمة من الرسائل الجديدة
    """
    logging.info(f"🔍 بدء سحب الرسائل الحديثة (آخر {minutes} دقيقة)...")
    
    client = TelegramClient('anon', Config.TELEGRAM_API_ID, Config.TELEGRAM_API_HASH)
    documents = []
    
    try:
        await client.start()
        channel = await client.get_entity(Config.CHANNEL_USERNAME)
        
        # تحديد الفترة الزمنية
        since_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        message_count = 0
        # سحب الرسائل الحديثة فقط
        async for message in client.iter_messages(channel, limit=100):  # حد أقصى 100 رسالة
            if message.date and message.date < since_time:
                break  # وصلنا لرسائل أقدم من الفترة
            
            if message.text:
                # 🏷️ تحديد نوع الرسالة (أيضاً في التحديثات الحديثة)
                doc_type = 'admin'  # الافتراضي: منشور رسمي
                
                if message.is_reply or message.fwd_from:
                    doc_type = 'student'
                
                documents.append({
                    "id": f"{channel.id}_{message.id}",
                    "text": message.text,
                    "date": message.date.isoformat() if message.date else "",
                    "link": f"https://t.me/{Config.CHANNEL_USERNAME}/{message.id}",
                    "type": doc_type  # 🏷️ البطاقة الجديدة
                })
                message_count += 1
        
        if message_count > 0:
            logging.info(f"✅ تم سحب {message_count} رسالة جديدة")
        else:
            logging.info("ℹ️ لا توجد رسائل جديدة")
        
        return documents
    
    except Exception as e:
        logging.error(f"❌ خطأ في سحب الرسائل الحديثة: {e}")
        return []
    
    finally:
        await client.disconnect()


# ============== V2: دالة السحب من المصادر المتعددة ==============

async def scrape_all_sources():
    """
    V2: يسحب الرسائل من كل المصادر في Config.TELEGRAM_SOURCES
    (القناة الرئيسية + جروب الإقامات + أي مصادر أخرى)
    """
    logging.info("="*60)
    logging.info("✨ V2: بدء عملية سحب الرسائل من *كل* المصادر...")
    logging.info("="*60)
    
    client = TelegramClient('anon', Config.TELEGRAM_API_ID, Config.TELEGRAM_API_HASH)
    all_documents = []
    
    try:
        await client.start()
        logging.info("✅ تم الاتصال بـ Telethon.")
        
        for source in Config.TELEGRAM_SOURCES:
            source_id = source["id"]
            source_tag = source["tag"]
            source_type = source.get("type", "public")
            
            # تخطي المصادر الفارغة
            if not source_id or source_id == "":
                logging.warning(f"⚠️ تخطي مصدر فارغ: {source_tag}")
                continue
            
            logging.info(f"\n🔍 --- بدء سحب المصدر: '{source_id}' (البطاقة: {source_tag}) ---")
            
            try:
                channel = await client.get_entity(source_id)
                
                # محاولة الانضمام (للقنوات العامة)
                if source_type == "public":
                    try:
                        await client(JoinChannelRequest(channel))
                        logging.info(f"  ✅ تم الانضمام لـ {source_id}")
                    except Exception:
                        pass  # منضم مسبقاً
                
                since_date = datetime.now(timezone.utc) - timedelta(days=Config.DAYS_LIMIT)
                message_count = 0
                
                # سحب الرسائل
                async for message in client.iter_messages(channel):
                    if message.date and message.date < since_date:
                        break
                    
                    if message.text:
                        # 🏷️ تحديد نوع الرسالة: أدمن أو طالب
                        doc_type = 'admin'
                        if message.is_reply or message.fwd_from:
                            doc_type = 'student'
                        
                        # إنشاء رابط مناسب (للجروبات الخاصة نستخدم c/ID)
                        if source_type == "private":
                            link = f"https://t.me/c/{channel.id}/{message.id}"
                        else:
                            link = f"https://t.me/{source_id}/{message.id}"
                        
                        all_documents.append({
                            "id": f"{channel.id}_{message.id}",
                            "text": message.text,
                            "date": message.date.isoformat() if message.date else "",
                            "link": link,
                            "type": doc_type,
                            "source_tag": source_tag  # 🆕 البطاقة الجديدة المهمة!
                        })
                        message_count += 1
                
                logging.info(f"  ✅ تم سحب {message_count} رسالة من '{source_id}'")
            
            except Exception as e:
                logging.error(f"  ❌ فشل سحب المصدر '{source_id}': {e}")
                if source_type == "private":
                    logging.warning(f"  ⚠️ تأكد أن حسابك (anon.session) منضم للجروب الخاص: {source_id}")
        
        logging.info("="*60)
        logging.info(f"✨ اكتمل السحب. إجمالي الرسائل: {len(all_documents)}")
        logging.info("="*60)
        return all_documents
    
    except Exception as e:
        logging.error(f"❌ خطأ فادح في السحب: {e}")
        return None
    
    finally:
        await client.disconnect()


# ============== دالة السحب المباشر الجديدة ==============

async def get_latest_admin_posts_live(count=5):
    """
    يسحب آخر المنشورات الرسمية (الأدمن) مباشرة من تليجرام.
    """
    logging.info("🔍 بدء سحب مباشر لآخر الأخبار...")
    client = TelegramClient('anon_live', Config.TELEGRAM_API_ID, Config.TELEGRAM_API_HASH)

    admin_posts = []

    try:
        await client.start()
        channel = await client.get_entity(Config.CHANNEL_USERNAME)

        # نسحب آخر 100 رسالة (لضمان العثور على 5 منشورات)
        async for message in client.iter_messages(channel, limit=100):

            # نستخدم نفس الفلتر الاحترافي: (ليست رداً وليست محولة)
            if message.text and not message.is_reply and not message.fwd_from:
                admin_posts.append({
                    "text": message.text,
                    "date": message.date.isoformat(),
                    "link": f"https://t.me/{Config.CHANNEL_USERNAME}/{message.id}"
                })

            # إذا وصلنا للعدد المطلوب، نتوقف
            if len(admin_posts) >= count:
                break

        return admin_posts

    except Exception as e:
        logging.error(f"حدث خطأ أثناء السحب المباشر: {e}")
        return []
    finally:
        await client.disconnect()
