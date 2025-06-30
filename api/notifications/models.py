from django.db import models


class EmailTemplate(models.Model):
    """
    Represents an email template used for notifications.
    Fields:
        name (CharField): The unique name of the email template.
        subject (CharField): The subject line for the email.
        html_file (FileField): The HTML file associated with the email template, uploaded to 'email_templates/html/'.
        plain_text_file (FileField): The plain text file for the email template, uploaded to 'email_templates/plain/'.
        created_at (DateTimeField): Timestamp when the template was created.
        updated_at (DateTimeField): Timestamp when the template was last updated.
    Methods:
        __str__(): Returns a string representation of the email template, including its name and subject.
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
    Represents an attachment file associated with an email template.
    Fields:
        template (ForeignKey): Reference to the related EmailTemplate.
        file (FileField): The file attached to the email template, uploaded to 'email_templates/attachments/'.
        created_at (DateTimeField): Timestamp when the attachment was created.
        updated_at (DateTimeField): Timestamp when the attachment was last updated.
    Methods:
        __str__(): Returns a string representation showing the template name and file name.
    """
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='email_templates/attachments/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Attachment for template: {}, file name: {}".format(self.template.name, self.file.name)
  
  
class EmailImage(models.Model):
    """
    Represents an image associated with an email template.
    Fields:
        template (ForeignKey): Reference to the related EmailTemplate.
        image (ImageField): The image file to be used in the email template.
        created_at (DateTimeField): Timestamp when the image was created.
        updated_at (DateTimeField): Timestamp when the image was last updated.
    Methods:
        __str__(): Returns a string representation showing the template name and image name.
    """
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='email_templates/images/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Image for template: {}, image name: {}".format(self.template.name, self.image.name)


class EmailStyle(models.Model):
    """
    Represents a style file associated with an email template.
    Attributes:
        template (ForeignKey): Reference to the related EmailTemplate.
        style_file (FileField): The file containing the style (e.g., CSS) for the email template.
        created_at (DateTimeField): Timestamp when the style was created.
        updated_at (DateTimeField): Timestamp when the style was last updated.
    Methods:
        __str__(): Returns a human-readable string representation of the EmailStyle instance.
    """
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='styles')
    style_file = models.FileField(upload_to='email_templates/styles/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Style for template: {}, style file name: {}".format(self.template.name, self.style_file.name)
