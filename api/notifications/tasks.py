import os
from celery import shared_task
from .utils import send_email_with_attachments, delete_email_files
from accounts.models import User

@shared_task
def send_email_task(
    subject,
    template_name,
    context,
    recipient_list,
    attachments=None,
    email_host_user=None,
    email_host_password=None,
    from_email=None
):
    """
    Sends an email with optional attachments asynchronously, supporting custom SMTP credentials.
    Args:
        subject (str): The subject of the email.
        template_name (str): The name of the email template to use.
        context (dict): Context data to render the template.
        recipient_list (list): List of recipient email addresses.
        attachments (list, optional): List of attachments to include in the email. Defaults to None.
        email_host_user (str, optional): SMTP username for the email host. Defaults to None.
        email_host_password (str, optional): SMTP password for the email host. Defaults to None.
        from_email (str, optional): From email address. Defaults to None.
    Returns:
        Any: The result of the send_email_with_attachments function.
    """
    return send_email_with_attachments(
        subject,
        template_name,
        context,
        recipient_list,
        attachments,
        email_host_user=email_host_user,
        email_host_password=email_host_password,
        from_email=from_email
    )


@shared_task
def delete_email_task(html_path, plain_path, attachment_paths=None, image_paths=None, style_paths=None):
    """
    Deletes email-related files including HTML, plain text, attachments, images, and styles.
    Args:
        html_path (str): Path to the HTML email file to be deleted.
        plain_path (str): Path to the plain text email file to be deleted.
        attachment_paths (list[str], optional): List of file paths for attachments to be deleted. Defaults to None.
        image_paths (list[str], optional): List of file paths for images to be deleted. Defaults to None.
        style_paths (list[str], optional): List of file paths for style files to be deleted. Defaults to None.
    Returns:
        Any: The result of the delete_email_files function, which handles the deletion process.
    """
    return delete_email_files(
        html_path,
        plain_path,
        attachment_paths=attachment_paths,
        image_paths=image_paths,
        style_paths=style_paths
    )


@shared_task
def send_newsletter_task(template_id, email_host_user=None, email_host_password=None, from_email=None):
    """
    Sends a newsletter email to all subscribed users using the specified email template and sender credentials.
    Args:
        template_id (int): The primary key of the EmailTemplate to use for the newsletter.
        email_host_user (str, optional): SMTP username for the email host. Defaults to None.
        email_host_password (str, optional): SMTP password for the email host. Defaults to None.
        from_email (str, optional): From email address. Defaults to None.
    Behavior:
        - Retrieves the email template and its attachments by the given template_id.
        - Gathers the email addresses of all users who are subscribed.
        - Sends an email with the template and attachments to all subscribed users.
    Raises:
        EmailTemplate.DoesNotExist: If no EmailTemplate with the given template_id exists.
    """
    from notifications.models import EmailTemplate  # Import here to avoid circular import
    template = EmailTemplate.objects.get(id=template_id)
    attachments = template.attachments.all()
    recipient_list = list(User.objects.filter(is_subscribed=True).values_list(
        'email', flat=True
        )
)
    if recipient_list:
        send_email_with_attachments(
            subject=template.subject,
            template_name=template.name,
            context={},
            recipient_list=recipient_list,
            attachments=[a.file.path for a in attachments],
            email_host_user=email_host_user,
            email_host_password=email_host_password,
            from_email=from_email
        )
