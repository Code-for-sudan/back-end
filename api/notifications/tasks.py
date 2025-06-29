import os
from celery import shared_task
from .utils import send_email_with_attachments, delete_email_files


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
