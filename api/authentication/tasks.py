import logging
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken # type: ignore
from django.utils.timezone import now
from celery import shared_task

# Create a logger for this celery task module
logger = logging.getLogger('celery_tasks.authentication')

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

