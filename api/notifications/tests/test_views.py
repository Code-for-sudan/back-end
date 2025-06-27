import tempfile
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from notifications.models import EmailTemplate
from notifications.serializers import EmailTemplateSerializer

User = get_user_model()

class EmailTemplateViewSetTestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com', password='password123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)
        self.template = EmailTemplate.objects.create(
            name="Welcome",
            subject="Welcome Email",
            html_content="<h1>Welcome</h1>",
            plain_text="Welcome",
        )
        self.url = reverse('emailtemplate-list')  # Make sure router is used in urls.py
        self.detail_url = reverse('emailtemplate-detail', kwargs={'pk': self.template.pk})

    def test_create_email_template(self):
        data = {
            "name": "Promotion",
            "subject": "Special Offer",
            "html_content": "<h1>50% OFF</h1>",
            "plain_text": "50% OFF!",
        }
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("data", response.data)
        self.assertEqual(response.data["data"]["name"], "Promotion")

    def test_create_email_template_invalid(self):
        # Missing required fields
        data = {"name": ""}
        response = self.client.post(self.url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)

    def test_update_email_template(self):
        data = {
            "subject": "Updated Subject"
        }
        response = self.client.patch(self.detail_url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["subject"], "Updated Subject")

    def test_retrieve_email_template(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["name"], self.template.name)

    def test_delete_email_template(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EmailTemplate.objects.filter(pk=self.template.pk).exists())
