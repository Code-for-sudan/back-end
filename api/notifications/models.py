from django.db import models


class EmailTemplate(models.Model):
    """
    Model representing an email template with both HTML and plain text versions.
    Fields:
        name (CharField): Unique name for the email template (max length 100).
        subject (CharField): Subject line for the email (max length 255).
        html_file (FileField): File containing the HTML version of the email template, uploaded to 'email_templates/html/'.
        plain_text_file (FileField): File containing the plain text version of the email template, uploaded to 'email_templates/plain/'.
        created_at (DateTimeField): Timestamp when the template was created (auto-set on creation).
        updated_at (DateTimeField): Timestamp when the template was last updated (auto-updated on save).
    Methods:
        __str__(): Returns the name of the email template.
    """
    name = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)

    html_file = models.FileField(upload_to='email_templates/html/')
    plain_text_file = models.FileField(upload_to='email_templates/plain/')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Email Template: {}, email subject: {}".format(self.name, self.subject)


class EmailAttachment(models.Model):
    """
    Model representing an attachment associated with an email template.
    Attributes:
        template (ForeignKey): Reference to the related EmailTemplate. Deleting the template will also delete its attachments.
        file (FileField): The file to be attached, uploaded to 'email_templates/attachments/' directory.
    """
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='email_templates/attachments/')

  
class EmailImage(models.Model):
    """
    Model representing an image associated with an email template.
    Attributes:
        template (ForeignKey): Reference to the related EmailTemplate. Deleting the template will also delete associated images.
        image (ImageField): The image file to be used in the email template, uploaded to 'email_templates/images/'.
    """
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='email_templates/images/')


class EmailStyle(models.Model):
    """
    Represents a style file associated with an email template.
    Attributes:
        template (ForeignKey): Reference to the related EmailTemplate instance.
        style_file (FileField): File field for uploading the style file, stored in 'email_templates/styles/'.
    """
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='styles')
    style_file = models.FileField(upload_to='email_templates/styles/')
