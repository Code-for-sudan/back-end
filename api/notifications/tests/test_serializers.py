import io
import unittest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError

from ..serializers import (
    EmailAttachmentSerializer,
    EmailImageSerializer,
    EmailStyleSerializer,
    EmailTemplateSerializer,
)
from ..models import (
    EmailAttachment,
    EmailImage,
    EmailStyle,
    EmailTemplate,
)
from django.test import TestCase

class TestSerializersUnityTestCase(TestCase):
    def setUp(self):
        self.template = EmailTemplate.objects.create(
            name="Test",
            subject="Subj",
            html_file=SimpleUploadedFile("a.html", b"<html></html>"),
            plain_text_file=SimpleUploadedFile("a.txt", b"plain")
        )

    # EmailAttachmentSerializer tests
    def test_attachment_valid_and_invalid(self):
        valid_file = SimpleUploadedFile("test.pdf", b"data", content_type="application/pdf")
        invalid_ext_file = SimpleUploadedFile("test.exe", b"data", content_type="application/octet-stream")
        too_large_file = SimpleUploadedFile("test.pdf", b"a" * (10 * 1024 * 1024 + 1), content_type="application/pdf")
        # Valid
        serializer = EmailAttachmentSerializer(data={"template": self.template.id, "file": valid_file})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Invalid extension
        serializer = EmailAttachmentSerializer(data={"template": self.template.id, "file": invalid_ext_file})
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)
        # Too large
        serializer = EmailAttachmentSerializer(data={"template": self.template.id, "file": too_large_file})
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_attachment_missing_file(self):
        serializer = EmailAttachmentSerializer(data={"template": self.template.id})
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    # EmailImageSerializer tests
    def test_image_valid_and_invalid(self):
        valid_image = SimpleUploadedFile("img.jpg", b"data", content_type="image/jpeg")
        invalid_ext_image = SimpleUploadedFile("img.gif", b"data", content_type="image/gif")
        too_large_image = SimpleUploadedFile("img.jpg", b"a" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")
        # Valid
        serializer = EmailImageSerializer(data={"template": self.template.id, "image": valid_image})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Invalid extension
        serializer = EmailImageSerializer(data={"template": self.template.id, "image": invalid_ext_image})
        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)
        # Too large
        serializer = EmailImageSerializer(data={"template": self.template.id, "image": too_large_image})
        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)

    def test_image_missing_file(self):
        serializer = EmailImageSerializer(data={"template": self.template.id})
        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)

    # EmailStyleSerializer tests
    def test_style_valid_and_invalid(self):
        valid_style = SimpleUploadedFile("style.css", b"body{}", content_type="text/css")
        invalid_ext_style = SimpleUploadedFile("style.txt", b"body{}", content_type="text/plain")
        too_large_style = SimpleUploadedFile("style.css", b"a" * (1 * 1024 * 1024 + 1), content_type="text/css")
        # Valid
        serializer = EmailStyleSerializer(data={"template": self.template.id, "style_file": valid_style})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Invalid extension
        serializer = EmailStyleSerializer(data={"template": self.template.id, "style_file": invalid_ext_style})
        self.assertFalse(serializer.is_valid())
        self.assertIn("style_file", serializer.errors)
        # Too large
        serializer = EmailStyleSerializer(data={"template": self.template.id, "style_file": too_large_style})
        self.assertFalse(serializer.is_valid())
        self.assertIn("style_file", serializer.errors)

    def test_style_missing_file(self):
        serializer = EmailStyleSerializer(data={"template": self.template.id})
        self.assertFalse(serializer.is_valid())
        self.assertIn("style_file", serializer.errors)

    # EmailTemplateSerializer tests
    def test_template_valid_and_missing_fields(self):
        html_file = SimpleUploadedFile("a.html", b"<html></html>")
        plain_text_file = SimpleUploadedFile("a.txt", b"plain")
        # Valid
        data = {
            "name": "Test",
            "subject": "Subject",
            "html_file": html_file,
            "plain_text_file": plain_text_file,
        }
        serializer = EmailTemplateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        # Missing all
        serializer = EmailTemplateSerializer(data={})
        self.assertFalse(serializer.is_valid())
        for field in ["name", "subject", "html_file", "plain_text_file"]:
            self.assertIn(field, serializer.errors)

    def test_template_partial_missing_fields(self):
        html_file = SimpleUploadedFile("a.html", b"<html></html>")
        # Missing plain_text_file
        data = {
            "name": "Test",
            "subject": "Subject",
            "html_file": html_file,
        }
        serializer = EmailTemplateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("plain_text_file", serializer.errors)

    def test_template_invalid_file_types(self):
        # Invalid html_file extension
        html_file = SimpleUploadedFile("a.txt", b"plain")
        plain_text_file = SimpleUploadedFile("a.txt", b"plain")
        data = {
            "name": "Test",
            "subject": "Subject",
            "html_file": html_file,
            "plain_text_file": plain_text_file,
        }
        serializer = EmailTemplateSerializer(data=data)
        # Should still be valid as no extension validation is enforced in serializer
        self.assertTrue(serializer.is_valid(), serializer.errors)
