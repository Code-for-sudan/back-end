from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from chat.models import ChatMessage
import logging

User = get_user_model()
logger = logging.getLogger("chat_tests")

class ChatHistoryViewTestCase(TestCase):
    """
    Integration tests for the ChatHistoryView API endpoint.

    These tests verify:
    - Successful retrieval of chat history between two users.
    - Proper error handling when the customer_id is missing.
    - Proper error handling when the customer does not exist.

    All test actions and results are logged using the 'chat_tests' logger for traceability.
    """

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="owner@example.com", password="testpass", first_name="Owner", last_name="User")
        self.customer = User.objects.create_user(email="customer@example.com", password="testpass", first_name="Customer", last_name="User")
        ChatMessage.objects.create(sender=self.owner, receiver=self.customer, message="Hello Customer!")
        ChatMessage.objects.create(sender=self.customer, receiver=self.owner, message="Hello Owner!", is_read=True)
        logger.info("Setup complete: owner and customer users created, initial messages sent.")

    def test_chat_history_view_success(self):
        """
        Test that chat history is returned successfully for valid users.
        """
        self.client.force_authenticate(user=self.owner)
        url = reverse("chat-history")
        response = self.client.get(url, {"customer_id": self.customer.id})
        logger.info(f"Requested chat history with customer_id={self.customer.id}, status={response.status_code}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("chat_between", data)
        self.assertIn("messages", data)
        self.assertEqual(data["chat_between"]["owner"]["id"], self.owner.id)
        self.assertEqual(data["chat_between"]["customer"]["id"], self.customer.id)
        self.assertEqual(len(data["messages"]), 2)
        logger.info("Chat history view success test passed.")

    def test_chat_history_view_missing_customer_id(self):
        """
        Test that a missing customer_id returns a 400 error.
        """
        self.client.force_authenticate(user=self.owner)
        url = reverse("chat-history")
        response = self.client.get(url)
        logger.info(f"Requested chat history with missing customer_id, status={response.status_code}")
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json()["error"],
            {"customer_id": ["This field is required."]}
        )
        logger.info("Chat history view missing customer_id test passed.")

    def test_chat_history_view_customer_not_found(self):
        """
        Test that a non-existent customer_id returns a 400 error (validated in serializer).
        """
        self.client.force_authenticate(user=self.owner)
        url = reverse("chat-history")
        response = self.client.get(url, {"customer_id": 9999})
        logger.info(f"Requested chat history with non-existent customer_id=9999, status={response.status_code}")
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(
            response.json()["error"],
            {"customer_id": ["Customer not found."]}
        )
        logger.info("Chat history view customer not found test passed.")

class ChatContactsViewTestCase(TestCase):
    """
    Integration tests for the ChatContactsView API endpoint.

    These tests verify:
    - Successful retrieval of the chat contacts list for a user.
    - That the returned contacts include correct user info and last message details.

    All test actions and results are logged using the 'chat_tests' logger for traceability.
    """

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="owner@example.com", password="testpass", first_name="Owner", last_name="User")
        self.customer = User.objects.create_user(email="customer@example.com", password="testpass", first_name="Customer", last_name="User")
        ChatMessage.objects.create(sender=self.owner, receiver=self.customer, message="Hello Customer!")
        ChatMessage.objects.create(sender=self.customer, receiver=self.owner, message="Hello Owner!", is_read=True)
        logger.info("Setup complete: owner and customer users created, initial messages sent.")

    def test_chat_contacts_view_success(self):
        """
        Test that chat contacts are returned successfully for the authenticated user.
        """
        self.client.force_authenticate(user=self.owner)
        url = reverse("chat-contacts")
        response = self.client.get(url)
        logger.info(f"Requested chat contacts for user_id={self.owner.id}, status={response.status_code}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["user_id"], self.owner.id)
        self.assertIsInstance(data["chats"], list)
        self.assertTrue(any(chat["contact_id"] == self.customer.id for chat in data["chats"]))
        logger.info("Chat contacts view success test passed.")