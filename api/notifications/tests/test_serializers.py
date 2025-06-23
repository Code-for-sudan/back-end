from django.core.files.uploadedfile import SimpleUploadedFile
from notifications.serializers import (
    EmailAttachmentSerializer,
    EmailImageSerializer,
    EmailStyleSerializer,
    EmailTemplateSerializer,
)
from notifications.models import (
    EmailAttachment,
    EmailImage,
    EmailStyle,
    EmailTemplate,
)
from unittest import mock

class EmailAttachmentSerializerTest(TestCase):
    def setUp(self):
        self.valid_file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        self.invalid_ext_file = SimpleUploadedFile("test.exe", b"file_content", content_type="application/octet-stream")
        self.large_file = SimpleUploadedFile("large.pdf", b"x" * (10 * 1024 * 1024 + 1), content_type="application/pdf")

    def test_valid_attachment(self):
        serializer = EmailAttachmentSerializer(data={"file": self.valid_file})
        self.assertTrue(serializer.is_valid())

    def test_invalid_extension(self):
        serializer = EmailAttachmentSerializer(data={"file": self.invalid_ext_file})
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_large_file(self):
        serializer = EmailAttachmentSerializer(data={"file": self.large_file})
        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

class EmailImageSerializerTest(TestCase):
    def setUp(self):
        self.valid_image = SimpleUploadedFile("img.png", b"img", content_type="image/png")
        self.invalid_ext_image = SimpleUploadedFile("img.gif", b"img", content_type="image/gif")
        self.large_image = SimpleUploadedFile("img.jpg", b"x" * (5 * 1024 * 1024 + 1), content_type="image/jpeg")

    def test_valid_image(self):
        serializer = EmailImageSerializer(data={"image": self.valid_image})
        self.assertTrue(serializer.is_valid())

    def test_invalid_extension(self):
        serializer = EmailImageSerializer(data={"image": self.invalid_ext_image})
        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)

    def test_large_image(self):
        serializer = EmailImageSerializer(data={"image": self.large_image})
        self.assertFalse(serializer.is_valid())
        self.assertIn("image", serializer.errors)

class EmailStyleSerializerTest(TestCase):
    def setUp(self):
        self.valid_style = SimpleUploadedFile("style.css", b"body{}", content_type="text/css")
        self.invalid_ext_style = SimpleUploadedFile("style.txt", b"body{}", content_type="text/plain")
        self.large_style = SimpleUploadedFile("style.css", b"x" * (1024 * 1024 + 1), content_type="text/css")

    def test_valid_style(self):
        serializer = EmailStyleSerializer(data={"style_file": self.valid_style})
        self.assertTrue(serializer.is_valid())

    def test_invalid_extension(self):
        serializer = EmailStyleSerializer(data={"style_file": self.invalid_ext_style})
        self.assertFalse(serializer.is_valid())
        self.assertIn("style_file", serializer.errors)

    def test_large_style(self):
        serializer = EmailStyleSerializer(data={"style_file": self.large_style})
        self.assertFalse(serializer.is_valid())
        self.assertIn("style_file", serializer.errors)

class EmailTemplateSerializerTest(TestCase):
    def setUp(self):
        self.html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        self.text_file = SimpleUploadedFile("template.txt", b"plain text", content_type="text/plain")
        self.attachment_file = SimpleUploadedFile("file.pdf", b"pdf", content_type="application/pdf")
        self.image_file = SimpleUploadedFile("img.png", b"img", content_type="image/png")
        self.style_file = SimpleUploadedFile("style.css", b"body{}", content_type="text/css")

        self.template_data = {
            "name": "Test Template",
            "subject": "Test Subject",
            "html_file": self.html_file,
            "plain_text_file": self.text_file,
            "attachments": [{"file": self.attachment_file}],
            "images": [{"image": self.image_file}],
            "styles": [{"style_file": self.style_file}],
        }

    @mock.patch("notifications.serializers.EmailAttachment.objects.create")
    @mock.patch("notifications.serializers.EmailImage.objects.create")
    @mock.patch("notifications.serializers.EmailStyle.objects.create")
    @mock.patch("notifications.serializers.EmailTemplate.objects.create")
    def test_create_template(self, mock_template_create, mock_style_create, mock_image_create, mock_attachment_create):
        mock_template = mock.Mock(spec=EmailTemplate)
        mock_template_create.return_value = mock_template
        serializer = EmailTemplateSerializer(data=self.template_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        template = serializer.save()
        mock_template_create.assert_called_once()
        mock_attachment_create.assert_called_once_with(template=mock_template, file=self.attachment_file)
        mock_image_create.assert_called_once_with(template=mock_template, image=self.image_file)
        mock_style_create.assert_called_once_with(template=mock_template, style_file=self.style_file)

    @mock.patch("notifications.serializers.EmailAttachment.objects.create")
    @mock.patch("notifications.serializers.EmailImage.objects.create")
    @mock.patch("notifications.serializers.EmailStyle.objects.create")
    def test_update_template(self, mock_style_create, mock_image_create, mock_attachment_create):
        template = mock.Mock(spec=EmailTemplate)
        template.attachments.all.return_value = mock.Mock()
        template.images.all.return_value = mock.Mock()
        template.styles.all.return_value = mock.Mock()
        serializer = EmailTemplateSerializer(instance=template, data=self.template_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated, template)
        self.assertTrue(mock_attachment_create.called)
        self.assertTrue(mock_image_create.called)
        self.assertTrue(mock_style_create.called)

