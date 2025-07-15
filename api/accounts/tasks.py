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
    Sends an account activation email to the specified user.
    Retrieves the user by their ID, generates an activation link, and sends an email using a predefined template.
    Logs an error if the email could not be sent.
    Args:
        user_id (int): The ID of the user to send the activation email to.
    Raises:
        Logs any exception encountered during the process.
    """
    try:
        user = User.objects.get(id=user_id)
        activation_link = generate_activation_link(user)
        context = {
            "activation_link": activation_link,
        }
        subject = "Activate your account"
        template_name = "activation"
        recipient_list = [user.email]
        send_email_with_attachments(subject, template_name, context, recipient_list)
    except Exception as e:
       logger.error(f"Failed to send activation email for user {user_id}: {e}", exc_info=True)
