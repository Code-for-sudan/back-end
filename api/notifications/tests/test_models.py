from django.core.files.uploadedfile import SimpleUploadedFile
from notifications.models import EmailTemplate, EmailAttachment, EmailImage, EmailStyle
from django.test import TestCase
from django.utils import timezone


class EmailTemplateModelTests(TestCase):
    def setUp(self):
        self.html_file = SimpleUploadedFile("template.html", b"<html><body>Hello</body></html>", content_type="text/html")
        self.plain_file = SimpleUploadedFile("template.txt", b"Hello", content_type="text/plain")

    def test_create_email_template(self):
        template = EmailTemplate.objects.create(
            name="Welcome",
            subject="Welcome Subject",
            html_file=self.html_file,
            plain_text_file=self.plain_file
        )
        self.assertEqual(template.name, "Welcome")
        self.assertEqual(template.subject, "Welcome Subject")
        self.assertTrue(template.html_file.name.startswith("email_templates/html/"))
        self.assertTrue(template.plain_text_file.name.startswith("email_templates/plain/"))
        self.assertIsNotNone(template.created_at)
        self.assertIsNotNone(template.updated_at)

    def test_email_template_str(self):
        template = EmailTemplate.objects.create(
            name="Reset",
            subject="Reset Password",
            html_file=self.html_file,
            plain_text_file=self.plain_file
        )
        self.assertEqual(str(template), "Email Template: Reset, email subject: Reset Password")

    def test_created_and_updated_at_auto_fields(self):
        template = EmailTemplate.objects.create(
            name="Notify",
            subject="Notification",
            html_file=self.html_file,
            plain_text_file=self.plain_file
        )
        now = timezone.now()
        self.assertTrue(abs((now - template.created_at).total_seconds()) < 5)
        self.assertTrue(abs((now - template.updated_at).total_seconds()) < 5)

class EmailAttachmentModelTests(TestCase):
    def setUp(self):
        self.html_file = SimpleUploadedFile("template.html", b"<html><body>Hello</body></html>")
        self.plain_file = SimpleUploadedFile("template.txt", b"Hello")
        self.attachment_file = SimpleUploadedFile("file.pdf", b"PDFDATA")
        self.template = EmailTemplate.objects.create(
            name="Attach",
            subject="Attachment",
            html_file=self.html_file,
            plain_text_file=self.plain_file
        )

    def test_create_email_attachment(self):
        attachment = EmailAttachment.objects.create(
            template=self.template,
            file=self.attachment_file
        )
        self.assertEqual(attachment.template, self.template)
        self.assertTrue(attachment.file.name.startswith("email_templates/attachments/"))

    def test_attachment_deleted_with_template(self):
        attachment = EmailAttachment.objects.create(
            template=self.template,
            file=self.attachment_file
        )
        self.template.delete()
        self.assertFalse(EmailAttachment.objects.filter(pk=attachment.pk).exists())

class EmailImageModelTests(TestCase):
    def setUp(self):
        self.html_file = SimpleUploadedFile("template.html", b"<html><body>Hello</body></html>")
        self.plain_file = SimpleUploadedFile("template.txt", b"Hello")
        self.image_file = SimpleUploadedFile("image.png", b"PNGDATA", content_type="image/png")
        self.template = EmailTemplate.objects.create(
            name="Image",
            subject="Image Subject",
            html_file=self.html_file,
            plain_text_file=self.plain_file
        )

    def test_create_email_image(self):
        image = EmailImage.objects.create(
            template=self.template,
            image=self.image_file
        )
        self.assertEqual(image.template, self.template)
        self.assertTrue(image.image.name.startswith("email_templates/images/"))

    def test_image_deleted_with_template(self):
        image = EmailImage.objects.create(
            template=self.template,
            image=self.image_file
        )
        self.template.delete()
        self.assertFalse(EmailImage.objects.filter(pk=image.pk).exists())

class EmailStyleModelTests(TestCase):
    def setUp(self):
        self.html_file = SimpleUploadedFile("template.html", b"<html><body>Hello</body></html>")
        self.plain_file = SimpleUploadedFile("template.txt", b"Hello")
        self.style_file = SimpleUploadedFile("style.css", b"body { color: red; }", content_type="text/css")
        self.template = EmailTemplate.objects.create(
            name="Style",
            subject="Style Subject",
            html_file=self.html_file,
            plain_text_file=self.plain_file
        )

    def test_create_email_style(self):
        style = EmailStyle.objects.create(
            template=self.template,
            style_file=self.style_file
        )
        self.assertEqual(style.template, self.template)
        self.assertTrue(style.style_file.name.startswith("email_templates/styles/"))

    def test_style_deleted_with_template(self):
        style = EmailStyle.objects.create(
            template=self.template,
            style_file=self.style_file
        )
        self.template.delete()
        self.assertFalse(EmailStyle.objects.filter(pk=style.pk).exists())
