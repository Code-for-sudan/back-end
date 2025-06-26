import unittest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from django.contrib.auth import get_user_model
from api.notifications.views import EmailStyleViewSet
from api.notifications.serializers import EmailStyleSerializer

User = get_user_model()

class EmailStyleViewSetCreateTestCase(unittest.TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.valid_payload = {
            "name": "Test Style",
            "css": "body { color: red; }"
        }
        self.invalid_payload = {
            "name": "",
            "css": "body { color: red; }"
        }

    def test_create_success(self):
        request = self.factory.post("/api/email-styles/", self.valid_payload, format="json")
        force_authenticate(request, user=self.admin_user)
        view = EmailStyleViewSet.as_view({"post": "create"})

        with patch.object(EmailStyleSerializer, 'is_valid', return_value=True), \
             patch.object(EmailStyleSerializer, 'save', return_value=None), \
             patch.object(EmailStyleSerializer, 'data', new_callable=MagicMock, return_value=self.valid_payload), \
             patch("api.notifications.views.logger") as mock_logger:
            response = view(request)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data["message"], "Email style created successfully.")
            self.assertEqual(response.data["data"], self.valid_payload)
            mock_logger.info.assert_called()

    def test_create_failure(self):
        request = self.factory.post("/api/email-styles/", self.invalid_payload, format="json")
        force_authenticate(request, user=self.admin_user)
        view = EmailStyleViewSet.as_view({"post": "create"})

        errors = {"name": ["This field may not be blank."]}
        with patch.object(EmailStyleSerializer, 'is_valid', return_value=False), \
             patch.object(EmailStyleSerializer, 'errors', new_callable=MagicMock, return_value=errors), \
             patch("api.notifications.views.logger") as mock_logger:
            response = view(request)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["message"], "Email style creation failed.")
            self.assertEqual(response.data["errors"], errors)
            mock_logger.error.assert_called()

    def test_update_success(self):
        # Mock instance and serializer
        instance = MagicMock()
        updated_payload = {"name": "Updated Style", "css": "body { color: blue; }"}
        request = self.factory.patch("/api/email-styles/1/", updated_payload, format="json")
        force_authenticate(request, user=self.admin_user)
        view = EmailStyleViewSet.as_view({"patch": "update"})

        with patch.object(EmailStyleViewSet, 'get_object', return_value=instance), \
             patch.object(EmailStyleSerializer, 'is_valid', return_value=True), \
             patch.object(EmailStyleSerializer, 'save', return_value=None), \
             patch.object(EmailStyleSerializer, 'data', new_callable=MagicMock, return_value=updated_payload), \
             patch("api.notifications.views.logger") as mock_logger, \
             patch.object(EmailStyleViewSet, 'get_serializer', return_value=EmailStyleSerializer()):
            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["message"], "Email style updated successfully.")
            self.assertEqual(response.data["data"], updated_payload)
            mock_logger.info.assert_called()

    def test_update_failure(self):
        instance = MagicMock()
        request = self.factory.patch("/api/email-styles/1/", self.invalid_payload, format="json")
        force_authenticate(request, user=self.admin_user)
        view = EmailStyleViewSet.as_view({"patch": "update"})
        errors = {"name": ["This field may not be blank."]}

        with patch.object(EmailStyleViewSet, 'get_object', return_value=instance), \
             patch.object(EmailStyleSerializer, 'is_valid', return_value=False), \
             patch.object(EmailStyleSerializer, 'errors', new_callable=MagicMock, return_value=errors), \
             patch("api.notifications.views.logger") as mock_logger, \
             patch.object(EmailStyleViewSet, 'get_serializer', return_value=EmailStyleSerializer()):
            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["message"], "Email style update failed.")
            self.assertEqual(response.data["errors"], errors)
            mock_logger.error.assert_called()

    def test_retrieve_success(self):
        instance = MagicMock()
        data = {"name": "Test Style", "css": "body { color: red; }"}
        request = self.factory.get("/api/email-styles/1/")
        force_authenticate(request, user=self.admin_user)
        view = EmailStyleViewSet.as_view({"get": "retrieve"})

        with patch.object(EmailStyleViewSet, 'get_object', return_value=instance), \
             patch.object(EmailStyleSerializer, 'data', new_callable=MagicMock, return_value=data), \
             patch("api.notifications.views.logger") as mock_logger, \
             patch.object(EmailStyleViewSet, 'get_serializer', return_value=EmailStyleSerializer()):
            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["message"], "Email style retrieved successfully.")
            self.assertEqual(response.data["data"], data)
            mock_logger.info.assert_called()

    def test_destroy_success(self):
        instance = MagicMock()
        instance.id = 1
        request = self.factory.delete("/api/email-styles/1/")
        force_authenticate(request, user=self.admin_user)
        view = EmailStyleViewSet.as_view({"delete": "destroy"})

        with patch.object(EmailStyleViewSet, 'get_object', return_value=instance), \
             patch.object(instance, 'delete', return_value=None), \
             patch("api.notifications.views.logger") as mock_logger:
            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertEqual(response.data["message"], "Email style deleted successfully.")
            mock_logger.info.assert_called()
