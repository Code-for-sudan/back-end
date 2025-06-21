import os
import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger("email")

def send_email_with_attachments(subject, template_name, context, recipient_list, attachments=None):
    """
    Sends an email using plain text and HTML templates with optional file attachments.
    """
    try:
        base_dir = os.path.join(settings.BASE_DIR, "notifications", "emails")

        html_content = render_to_string(
            os.path.join("emails", "templates", f"{template_name}.html"), context
        )

        plain_text_path = os.path.join(base_dir, "plain_text", f"{template_name}.txt")
        with open(plain_text_path, encoding="utf-8") as file:
            plain_text_content = file.read().format(**context)

        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
        )
        email.attach_alternative(html_content, "text/html")

        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    email.attach_file(file_path)
                else:
                    logger.warning(f"Attachment not found: {file_path}")

        email.send(fail_silently=False)
        logger.info(f"Email sent successfully to: {recipient_list}")
        return "Email sent"

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return f"Error: {e}"
