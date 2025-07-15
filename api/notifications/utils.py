import os
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger("email")

def send_email_with_attachments(subject, template_name, context, recipient_list, attachments=None):
    """
    Sends an email with both HTML and plain text content, and optional file attachments.

    Args:
        subject (str): The subject line of the email.
        template_name (str): The base name of the email template (without extension).
        context (dict): Context variables to render into the email templates.
        recipient_list (list): List of recipient email addresses.
        attachments (list, optional): List of file paths to attach to the email. Defaults to None.

    Returns:
        str: "Email sent" if successful, or an error message if sending fails.

    Raises:
        Exception: Any exception encountered during email sending is logged and returned as an error message.
    """
    try:
        base_dir = os.path.join(settings.BASE_DIR, "media", "email_templates")
        html_content = render_to_string(os.path.join(base_dir, 'html', f"{template_name}.html"), context)
        plain_text_path = os.path.join(base_dir, "plain", f"{template_name}.txt")
        logger.error(f'context: {context}')
        with open(plain_text_path, encoding="utf-8") as file:
            plain_text_raw = file.read()
            if context:
                plain_text_content = plain_text_raw.format(**context)
            else:
                plain_text_content = plain_text_raw

        # Overwrite the email and password with the no-reply email settings
        

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
        )
        email.attach_alternative(html_content, "text/html")

        if attachments:
            for file in attachments:
                if os.path.exists(file):
                    email.attach_file(file)
                else:
                    logger.warning(f"Attachment not found: {file}")

        email.send(fail_silently=False)
        logger.info(f"Email sent successfully to: {recipient_list}")
        return "Email sent"

    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
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
