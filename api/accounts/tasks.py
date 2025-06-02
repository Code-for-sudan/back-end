import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings

logger = logging.getLogger('email_tasks')

@shared_task(queue='email')
def send_email_task(recipients, subject, body, attachments=None):
    """
    Send an email (plain or with attachments) to multiple recipients.
    Args:
        recipients (list): List of email addresses.
        subject (str): Email subject.
        body (str): Email body (plain text).
        attachments (list of dict, optional): Each dict should have
            {'filename': ..., 'path': ..., 'mimetype': ...}
    Returns:
        dict: Status and reason for success or failure.
    Logging:
        - Logs an error if recipients are missing or not a list.
        - Logs an error if an attachment cannot be read or attached.
        - Logs an error if sending the email fails.
        - Logs info on successful email sending.
    """
    if not recipients or not isinstance(recipients, list):
        logger.error("No recipients provided or recipients is not a list.")
        return {'status': 'failure', 'reason': 'No recipients provided.'}

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipients,
        )

        # Attach files if provided
        if attachments:
            for att in attachments:
                try:
                    with open(att['path'], 'rb') as f:
                        email.attach(att['filename'], f.read(), att.get('mimetype', 'application/octet-stream'))
                except Exception as e:
                    logger.error(f"Failed to attach file {att['path']}: {e}")
                    return {'status': 'failure', 'reason': f"Attachment error: {e}"}

        email.send()
        logger.info(f"Email sent to {recipients} with subject '{subject}'.")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"Failed to send email to {recipients}: {e}")
        return {'status': 'failure', 'reason': str(e)}