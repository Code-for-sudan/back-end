import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    """
    Configuration class for email relay service.
    Attributes:
        SMTP_HOST (str): The hostname of the SMTP server, loaded from the 'SMTP_HOST' environment variable.
        SMTP_PORT (int): The port number for the SMTP server, loaded from the 'SMTP_PORT' environment variable.
        SMTP_USER (str): The username for SMTP authentication, loaded from the 'SMTP_USER' environment variable.
        SMTP_PASSWORD (str): The password for SMTP authentication, loaded from the 'SMTP_PASSWORD' environment variable.
        CELERY_BROKER_URL (str): The URL for the Celery broker, loaded from the 'CELERY_BROKER_URL' environment variable.
        CELERY_RESULT_BACKEND (str): The backend URL for Celery results, loaded from the 'CELERY_RESULT_BACKEND' environment variable.
    """
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT'))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND')
