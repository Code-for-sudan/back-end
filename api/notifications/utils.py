import os
import logging
import requests
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger("email")

def send_email_with_attachments(
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
    Sends an email with optional attachments using a Flask relay server.

    Renders both HTML and plain text email templates with the provided context, 
    and sends the email to the specified recipient list via an external Flask server.

    Args:
        subject (str): Subject of the email.
        template_name (str): Name of the email template (without extension).
        context (dict): Context data for rendering the templates.
        recipient_list (list): List of recipient email addresses.
        attachments (list, optional): List of file paths to attach to the email. Defaults to None.
        email_host_user (str, optional): SMTP username. Defaults to None.
        email_host_password (str, optional): SMTP password. Defaults to None.
        from_email (str, optional): Sender's email address. Defaults to None.

    Returns:
        str: Response text from the Flask relay server, or error message if sending fails.

    Raises:
        Exception: Logs and returns error message if any exception occurs during processing.
    """
    try:
        base_dir = os.path.join(settings.BASE_DIR, "media", "email_templates")
        html_content = render_to_string(f"html/{template_name}.html", context)
        plain_text_path = os.path.join(base_dir, "plain", f"{template_name}.txt")
        with open(plain_text_path, encoding="utf-8") as file:
            plain_text_raw = file.read()
            if context:
                plain_text_content = plain_text_raw.format(**context)
            else:
                plain_text_content = plain_text_raw

        data = {
            "subject": subject,
            "template_name": template_name,
            "context": context,
            "recipient_list": recipient_list,
            "attachments": attachments or [],
            "from_email": from_email or settings.EMAIL_HOST_USER,
            "plain_text": plain_text_content,
            "html_content": html_content,
            "smtp_host": email_host_user or settings.EMAIL_HOST,
            "smtp_port": settings.EMAIL_PORT,
            "smtp_user": email_host_user or settings.EMAIL_HOST_USER,
            "smtp_password": email_host_password or settings.EMAIL_HOST_PASSWORD,
        }

        # Send to Flask relay
        response = requests.post("http://197.252.2.249:5000/send-email", json=data)
        logger.info(f"Email relay response: {response.text}")
        return response.text

    except Exception as e:
        logger.error(f"Failed to relay email: {e}", exc_info=True)
        return f"Error: {e}"


def delete_email_files(html_path, plain_path, attachment_paths=None, image_paths=None, style_paths=None):
    """
    Deletes specified email-related files from the filesystem.
    Parameters:
        html_path (str): Path to the HTML email file to delete.
        plain_path (str): Path to the plain text email file to delete.
        attachment_paths (list[str], optional): List of file paths for attachments to delete.
        image_paths (list[str], optional): List of file paths for images to delete.
        style_paths (list[str], optional): List of file paths for style files to delete.
    Notes:
        - Ignores any paths that are None or do not exist.
        - Prints an error message if a file cannot be deleted.
    """
    paths = [html_path, plain_path]
    if attachment_paths:
        paths.extend(attachment_paths)
    if image_paths:
        paths.extend(image_paths)
    if style_paths:
        paths.extend(style_paths)
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.info(f"Failed to delete {path}: {e}")
