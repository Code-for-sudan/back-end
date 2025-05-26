"""
Celery configuration file for Django API project.
"""
import environ, os, logging
from __future__ import absolute_import, unicode_literals
from celery import Celery
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken # type: ignore
from django.utils.timezone import now


# Load environment variables from .env file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

# Create celery app instance
app = Celery('sudamall_backend')

# Load celery config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Set the autodiscover to True
app.autodiscover_tasks()

# Create a logger for Celery tasks
logger = logging.getLogger('celery')

@app.task(bind=True)
def debug_task(self):
    """
    A Celery task for debugging purposes.

    This task prints the details of the current request to the console.
    It is primarily used for testing and debugging Celery task execution.

    Args:
        self: The task instance that is bound to this method.

    Example:
        When this task is called, it will output the request details:
        >>> debug_task.apply_async()
        Request: <Context details of the task>
    """
    print(f'Request: {self.request!r}')

@shared_task
def clean_expired_blacklisted_tokens():
    """
    Deletes expired blacklisted tokens from the database.
    This function queries the BlacklistedToken model for tokens that have expired
    (i.e., their expiration date is less than the current time) and deletes them.
    It logs the number of deleted tokens if successful, or logs an error message
    if an exception occurs during the process.
    Raises:
        Exception: If there is an error during the deletion process.
    """
    
    try:
        expired_tokens = BlacklistedToken.objects.filter(token__expires_at__lt=now())
        count = expired_tokens.count()
        expired_tokens.delete()
        logger.info("Deleted {} expired blacklisted tokens.".format(count))
    except Exception as e:
        logger.error("Failed to delete expired blacklisted tokens: {}".format(e))


# Import periodic tasks for Celery Beat
from celery.schedules import crontab
from celery import shared_task
