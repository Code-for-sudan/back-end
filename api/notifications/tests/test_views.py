import os
from django.test import TestCase, override_settings
from django.core.cache import cache
from rest_framework import status # type: ignore
from rest_framework.test import APITestCase # type: ignore
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch
from notifications.models import EmailTemplate
from django.core.files.uploadedfile import SimpleUploadedFile

# Get the user model
User = get_user_model()



class EmailTemplateViewSetTests(APITestCase):
    def setUp(self):
        # Create an admin user and authenticate
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass',
            first_name='Admin',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
        self.list_url = reverse('emailtemplate')

    def test_admin_can_list_email_templates(self):
        EmailTemplate.objects.create(name="Welcome", subject="Welcome!")
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(isinstance(response.data, list) or "results" in response.data)

    def test_admin_can_create_email_template(self):
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("plain.txt", b"plain text", content_type="text/plain")
        data = {
            "name": "Reset Password",
            "subject": "Reset your password",
            "body": "Click here to reset your password.",
            "html_file": html_file,
            "plain_text_file": plain_file,
        }
        response = self.client.post(self.list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(EmailTemplate.objects.count(), 1)
        self.assertEqual(EmailTemplate.objects.first().name, "Reset Password")

    def test_admin_can_retrieve_email_template(self):
        template = EmailTemplate.objects.create(name="Notify", subject="Subject")
        url = reverse('emailtemplate-detail', args=[template.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Notify")

    def test_admin_can_update_email_template(self):
        template = EmailTemplate.objects.create(name="Old", subject="Old")
        url = reverse('emailtemplate-detail', args=[template.id])
        html_file = SimpleUploadedFile("template.html", b"<html></html>", content_type="text/html")
        plain_file = SimpleUploadedFile("plain.txt", b"plain text", content_type="text/plain")
        data = {
            "name": "Updated",
            "subject": "Reset your password",
            "body": "Click here to reset your password.",
            "html_file": html_file,
            "plain_text_file": plain_file,
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        template.refresh_from_db()
        self.assertEqual(template.name, "Updated")

    def test_admin_can_delete_email_template(self):
        template = EmailTemplate.objects.create(name="Delete", subject="Delete")
        url = reverse('emailtemplate-detail', args=[template.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EmailTemplate.objects.filter(id=template.id).exists())

    def test_non_admin_cannot_access_email_templates(self):
        user = User.objects.create_user(
            email='user@example.com',
            password='userpass',
            first_name='User',
            last_name='User'
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

