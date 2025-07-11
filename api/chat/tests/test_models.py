import logging
from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.models import ChatMessage

User = get_user_model()
logger = logging.getLogger("chat_tests")

class ChatMessageModelTestCase(TestCase):
    """
    Integration tests for the ChatMessage model.

    These tests verify:
    - Creation of chat messages and field values.
    - Preview method for short and long messages.
    - String representation of a chat message.
    All test actions are logged using the 'chat_tests' logger for traceability.
    """

    def setUp(self):
        self.sender = User.objects.create_user(email="sender@example.com", password="testpass")
        self.receiver = User.objects.create_user(email="receiver@example.com", password="testpass")
        logger.info("Created sender and receiver users.")

    def test_create_chat_message(self):
        msg = ChatMessage.objects.create(sender=self.sender, receiver=self.receiver, message="Hello!")
        logger.info(f"Created ChatMessage: {msg}")
        self.assertEqual(msg.sender, self.sender)
        self.assertEqual(msg.receiver, self.receiver)
        self.assertEqual(msg.message, "Hello!")
        self.assertFalse(msg.is_read)
        self.assertIsNotNone(msg.timestamp)

    def test_get_message_preview_short(self):
        msg = ChatMessage.objects.create(sender=self.sender, receiver=self.receiver, message="Short message")
        logger.info(f"Message preview (short): {msg.get_message_preview()}")
        self.assertEqual(msg.get_message_preview(), "Short message")

    def test_get_message_preview_long(self):
        long_text = "This is a very long message that should be truncated in the preview."
        msg = ChatMessage.objects.create(sender=self.sender, receiver=self.receiver, message=long_text)
        preview = msg.get_message_preview(length=20)
        logger.info(f"Message preview (long): {preview}")
        self.assertEqual(preview, long_text[:20] + "...")

    def test_str_method(self):
        msg = ChatMessage.objects.create(sender=self.sender, receiver=self.receiver, message="Test message")
        expected = f"{self.sender} to {self.receiver}: Test message"
        logger.info(f"String representation: {str(msg)}")
        self.assertEqual(str(msg), expected)