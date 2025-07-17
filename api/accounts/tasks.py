import logging
from celery import shared_task
from django.conf import settings
from accounts.utils import generate_activation_link
from notifications.utils import send_email_with_attachments
from accounts.models import User

# Create the logger for this module
logger = logging.getLogger('accounts_tasks')

@shared_task
def send_activation_email_task(user_id):
    """
    Sends an account activation email to the user with the specified user ID.
    Retrieves the user from the database, generates an activation link, and sends an email using dedicated sender credentials.
    Logs an error if the email could not be sent.
    Args:
        user_id (int): The ID of the user to send the activation email to.
    Raises:
        Logs any exception that occurs during the process.
    """
    try:
        user = User.objects.get(id=user_id)
        activation_link = generate_activation_link(user)
        logger.error(activation_link)
        context = {
            "activation_link": activation_link,
        }
        subject = "Activate your account"
        template_name = "activation"
        recipient_list = [user.email]
        # Use dedicated sender credentials for activation emails
        send_email_with_attachments(
            subject,
            template_name,
            context,
            recipient_list,
            email_host_user=settings.EMAIL_HOST_USER_SECURITY,
            email_host_password=settings.EMAIL_HOST_PASSWORD_SECURITY,
            from_email=settings.EMAIL_HOST_USER_SECURITY
        )
    except Exception as e:
        logger.error(f"Failed to send activation email for user {user_id}: {e}", exc_info=True)
