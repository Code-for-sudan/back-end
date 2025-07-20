import smtplib
from email.message import EmailMessage
from celery import Celery
import logging
from config import Config

celery = Celery('email_relay', broker=Config.CELERY_BROKER_URL)
celery.conf.update(
    broker_url=Config.CELERY_BROKER_URL,
    result_backend=Config.CELERY_RESULT_BACKEND
)

logging.basicConfig(
    filename='email_relay.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

@celery.task
def send_email_task(data):
    try:
        msg = EmailMessage()
        msg['Subject'] = data['subject']
        msg['From'] = data['from_email']
        msg['To'] = ', '.join(data['recipient_list'])
        msg.set_content(data['plain_text'])
        msg.add_alternative(data['html_content'], subtype='html')
        for file_path in data.get('attachments', []):
            with open(file_path, 'rb') as f:
                msg.add_attachment(f.read(), filename=file_path.split('/')[-1])
        with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as smtp:
            smtp.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
            smtp.send_message(msg)
        logger.info(f"Email sent to {msg['To']}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")