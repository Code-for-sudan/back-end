import os
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from notifications.serializers import (
    EmailAttachmentSerializer,
    EmailImageSerializer,
    EmailStyleSerializer,
    EmailTemplateSerializer
)
from notifications.models import (
    EmailAttachment,
    EmailImage,
    EmailStyle,
    EmailTemplate
)

class EmailAttachmentSerializerTest(TestCase):
    def test_valid_attachment(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.png')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1.png", f.read(), content_type="image/jpeg")
        serializer = EmailAttachmentSerializer(data={'file': file})
        serializer.is_valid()
        self.assertTrue(serializer.is_valid())

    def test_invalid_extension(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1 copy.png.sdf')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1 copy.png.sdf", f.read(), content_type="image/jpeg")
        serializer = EmailAttachmentSerializer(data={'file': file})
        serializer.is_valid()
        self.assertIn('file', serializer.errors)

    def test_invalid_size(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_3.jpg')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_3.jpg", f.read(), content_type="image/jpeg")
        serializer = EmailAttachmentSerializer(data={'file': file})
        serializer.is_valid()
        self.assertIn('file', serializer.errors)

class EmailImageSerializerTest(TestCase):
    def test_valid_image(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.png')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1.png", f.read(), content_type="image/jpeg")
        serializer = EmailAttachmentSerializer(data={'file': file})

    def test_invalid_extension(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1 copy.png.sdf')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1 copy.png.sdf", f.read(), content_type="image/jpeg")
        serializer = EmailAttachmentSerializer(data={'file': file})
        serializer.is_valid()
        self.assertIn('file', serializer.errors)

    def test_invalid_size(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_3.jpg')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_3.jpg", f.read(), content_type="image/jpeg")
        serializer = EmailAttachmentSerializer(data={'file': file})
        serializer.is_valid()
        self.assertIn('file', serializer.errors)

class EmailStyleSerializerTest(TestCase):
    def test_valid_style(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.pdf')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1.pdf", f.read(), content_type="application/pdf")
        serializer = EmailAttachmentSerializer(data={'file': file})
        self.assertTrue(serializer.is_valid())

    def test_invalid_extension(self):
        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1 copy.pdfww')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1 copy.pdfww", f.read(), content_type="application/pdf")
        serializer = EmailAttachmentSerializer(data={'file': file})
        serializer.is_valid()
        self.assertIn('file', serializer.errors)

    # def test_invalid_size(self):
    #     path = os.path.join(os.path.dirname(__file__), 'media')
    #     with open(path, 'rb') as f:
    #         file = SimpleUploadedFile("test.pdf", f.read(), content_type="application/pdf")
    #     serializer = EmailAttachmentSerializer(data={'file': file})
    #     self.assertIn('style_file', serializer.errors)

class EmailTemplateSerializerTest(TestCase):
    def test_create_template_with_nested(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("plain.txt", b"plain text", content_type="text/plain")
        attachment = SimpleUploadedFile("file.pdf", b"pdf", content_type="application/pdf")
        style = SimpleUploadedFile("style.css", b"body{}", content_type="text/css")

        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.png')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1.png", f.read(), content_type="image/jpeg")
            
        data = {
            "name": "Test Template",
            "subject": "Subject",
            "html_file": html_file,
            "plain_text_file": plain_file,
            "attachments": [{"file": attachment}],
            "images": [{"image": file}],
            "styles": [{"style_file": style}],
        }
        serializer = EmailTemplateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        template = serializer.save()
        self.assertEqual(template.attachments.count(), 1)
        self.assertEqual(template.images.count(), 1)
        self.assertEqual(template.styles.count(), 1)

    def test_update_template_with_nested(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("plain.txt", b"plain text", content_type="text/plain")
        template = EmailTemplate.objects.create(
            name="Old Name", subject="Old", html_file=html_file, plain_text_file=plain_file
        )
        EmailAttachment.objects.create(template=template, file=SimpleUploadedFile("old.pdf", b"old", content_type="application/pdf"))
        EmailImage.objects.create(template=template, image=SimpleUploadedFile("old.jpg", b"old", content_type="image/jpeg"))
        EmailStyle.objects.create(template=template, style_file=SimpleUploadedFile("old.css", b"old", content_type="text/css"))

        new_attachment = SimpleUploadedFile("new.pdf", b"new", content_type="application/pdf")
        new_style = SimpleUploadedFile("new.css", b"new", content_type="text/css")

        path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.png')
        with open(path, 'rb') as f:
            file = SimpleUploadedFile("test_1.png", f.read(), content_type="image/jpeg")
    
        data = {
            "name": "New Name",
            "subject": "New",
            "html_file": html_file,
            "plain_text_file": plain_file,
            "attachments": [{"file": new_attachment}],
            "images": [{"image": file}],
            "styles": [{"style_file": new_style}],
        }
        serializer = EmailTemplateSerializer(instance=template, data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.name, "New Name")
        self.assertEqual(updated.attachments.count(), 1)
        self.assertEqual(updated.images.count(), 1)
        self.assertEqual(updated.styles.count(), 1)
        