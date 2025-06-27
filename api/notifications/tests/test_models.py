import unittest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from ..models import EmailTemplate, EmailAttachment, EmailImage, EmailStyle

from django.test import TestCase

class EmailModelsTestCase(TestCase):
    def test_email_template_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>")
        plain_file = SimpleUploadedFile("template.txt", b"plain text")
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
        self.assertTrue(str(template).startswith("Email Template: Welcome, email subject: Welcome Subject"))
        self.assertLessEqual(template.created_at, timezone.now())
        self.assertLessEqual(template.updated_at, timezone.now())

    def test_email_attachment_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>")
        plain_file = SimpleUploadedFile("template.txt", b"plain text")
        template = EmailTemplate.objects.create(
            name="AttachmentTest",
            subject="Subject",
            html_file=html_file,
            plain_text_file=plain_file,
        )
        attachment_file = SimpleUploadedFile("file.pdf", b"pdf content")
        attachment = EmailAttachment.objects.create(
            template=template,
            file=attachment_file,
        )
        self.assertEqual(attachment.template, template)
        self.assertTrue(attachment.file.name.startswith("email_templates/attachments/"))
        self.assertIn("file.pdf", attachment.file.name)
        self.assertTrue(str(attachment).startswith("Attachment for template: AttachmentTest, file name: email_templates/attachments/"))
        self.assertLessEqual(attachment.created_at, timezone.now())
        self.assertLessEqual(attachment.updated_at, timezone.now())

    def test_email_image_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>")
        plain_file = SimpleUploadedFile("template.txt", b"plain text")
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
        self.assertIn("image.png", image.image.name)
        self.assertTrue(str(image).startswith("Image for template: ImageTest, image name: email_templates/images/"))
        self.assertLessEqual(image.created_at, timezone.now())
        self.assertLessEqual(image.updated_at, timezone.now())

    def test_email_style_creation(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>")
        plain_file = SimpleUploadedFile("template.txt", b"plain text")
        template = EmailTemplate.objects.create(
            name="StyleTest",
            subject="Subject",
            html_file=html_file,
            plain_text_file=plain_file,
        )
        style_file = SimpleUploadedFile("style.css", b"body { color: red; }")
        style = EmailStyle.objects.create(
            template=template,
            style_file=style_file,
        )
        self.assertEqual(style.template, template)
        self.assertTrue(style.style_file.name.startswith("email_templates/styles/"))
        self.assertIn("style.css", style.style_file.name)
        self.assertTrue(str(style).startswith("Style for template: StyleTest, style file name: email_templates/styles/"))
        self.assertLessEqual(style.created_at, timezone.now())
        self.assertLessEqual(style.updated_at, timezone.now())
