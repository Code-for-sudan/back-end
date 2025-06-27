from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ..models import EmailTemplate, EmailAttachment, EmailImage, EmailStyle
from django.test import TestCase

class EmailModelsTestCase(TestCase):
    def test_email_template_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("template.txt", b"plain text", content_type="text/plain")
        template = EmailTemplate.objects.create(
            name="Welcome",
            subject="Welcome Subject",
            html_file=html_file,
            plain_text_file=plain_file,
        )
        self.assertEqual(template.name, "Welcome")
        self.assertEqual(template.subject, "Welcome Subject")
        self.assertTrue(template.html_file.name.startswith("email_templates/html/"))
        self.assertTrue(template.plain_text_file.name.startswith("email_templates/plain/"))
        self.assertIn("Welcome", str(template))
        self.assertLessEqual(template.created_at, timezone.now())
        self.assertLessEqual(template.updated_at, timezone.now())

    def test_email_attachment_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("template.txt", b"plain text", content_type="text/plain")
        template = EmailTemplate.objects.create(
            name="AttachmentTest",
            subject="Subject",
            html_file=html_file,
            plain_text_file=plain_file,
        )
        attachment_file = SimpleUploadedFile("file.pdf", b"pdf content", content_type="application/pdf")
        attachment = EmailAttachment.objects.create(
            template=template,
            file=attachment_file,
        )
        self.assertEqual(attachment.template, template)
        self.assertTrue(attachment.file.name.startswith("email_templates/attachments/"))
        self.assertTrue(attachment.file.name.endswith(".pdf"))
        self.assertIn("AttachmentTest", str(attachment))
        self.assertLessEqual(attachment.created_at, timezone.now())
        self.assertLessEqual(attachment.updated_at, timezone.now())

    def test_email_image_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("template.txt", b"plain text", content_type="text/plain")
        template = EmailTemplate.objects.create(
            name="ImageTest",
            subject="Subject",
            html_file=html_file,
            plain_text_file=plain_file,
        )
        image_file = SimpleUploadedFile("image.png", b"imagecontent", content_type="image/png")
        image = EmailImage.objects.create(
            template=template,
            image=image_file,
        )
        self.assertEqual(image.template, template)
        self.assertTrue(image.image.name.startswith("email_templates/images/"))
        self.assertTrue(image.image.name.endswith(".png"))
        self.assertIn("ImageTest", str(image))
        self.assertLessEqual(image.created_at, timezone.now())
        self.assertLessEqual(image.updated_at, timezone.now())

    def test_email_style_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("template.txt", b"plain text", content_type="text/plain")
        template = EmailTemplate.objects.create(
            name="StyleTest",
            subject="Subject",
            html_file=html_file,
            plain_text_file=plain_file,
        )
        style_file = SimpleUploadedFile("style.css", b"body { color: red; }", content_type="text/css")
        style = EmailStyle.objects.create(
            template=template,
            style_file=style_file,
        )
        self.assertEqual(style.template, template)
        self.assertTrue(style.style_file.name.startswith("email_templates/styles/"))
        self.assertTrue(style.style_file.name.endswith(".css"))
        self.assertIn("StyleTest", str(style))
        self.assertLessEqual(style.created_at, timezone.now())
        self.assertLessEqual(style.updated_at, timezone.now())
