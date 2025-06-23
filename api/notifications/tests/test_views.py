from rest_framework.authtoken.models import Token
from notifications.models import EmailTemplate
from accounts.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse



class EmailTemplateViewSetTests(APITestCase):
    """
    Test suite for EmailTemplateViewSet in notifications app.
    Covers CRUD operations and permission checks.
    """

    def setUp(self):
        # Create admin user and authenticate
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123',
            first_name='Admin',
            last_name='User'
        )
        self.client.force_authenticate(user=self.admin_user)
        self.base_url = reverse('emailtemplate-list')
        self.valid_data = {
            "name": "Welcome Email",
            "subject": "Welcome!",
            "body": "Hello, welcome to our platform."
        }

    def test_create_email_template(self):
        response = self.client.post(self.base_url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], self.valid_data['name'])

    def test_list_email_templates(self):
        EmailTemplate.objects.create(**self.valid_data)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_retrieve_email_template(self):
        template = EmailTemplate.objects.create(**self.valid_data)
        url = reverse('emailtemplate-detail', args=[template.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], template.name)

    def test_update_email_template(self):
        template = EmailTemplate.objects.create(**self.valid_data)
        url = reverse('emailtemplate-detail', args=[template.id])
        update_data = {"subject": "Updated Subject"}
        response = self.client.patch(url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subject'], "Updated Subject")

    def test_delete_email_template(self):
        template = EmailTemplate.objects.create(**self.valid_data)
        url = reverse('emailtemplate-detail', args=[template.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EmailTemplate.objects.filter(id=template.id).exists())

    def test_permission_denied_for_non_admin(self):
        # Create a non-admin user
        user = User.objects.create_user(
            email='user@example.com',
            password='userpass123',
            first_name='Normal',
            last_name='User'
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(self.base_url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
