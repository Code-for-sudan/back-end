from celery import shared_task
from .utils import send_email_with_attachments


@shared_task
def send_email_task(subject, template_name, context, recipient_list, attachments=None):
    """
    Sends an email with optional attachments asynchronously.
    Args:
        subject (str): The subject of the email.
        template_name (str): The name of the email template to use.
        context (dict): Context data to render the template.
        recipient_list (list): List of recipient email addresses.
        attachments (list, optional): List of attachments to include in the email. Defaults to None.
    Returns:
        Any: The result of the send_email_with_attachments function.
    """
    return send_email_with_attachments(subject, template_name, context, recipient_list, attachments)
