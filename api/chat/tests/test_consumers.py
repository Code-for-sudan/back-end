import pytest
import logging
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.test import override_settings
from api.asgi import application

logger = logging.getLogger("chat_tests")
User = get_user_model()

@pytest.mark.django_db(transaction=True)
class TestChatConsumer:
    @pytest.fixture(autouse=True)
    def set_channels_layer(self, settings):
        settings.CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

    @pytest.fixture
    def user(self, db):
        return User.objects.create_user(email="testuser@example.com", password="testpass")

    @pytest.fixture
    def user2(self, db):
        return User.objects.create_user(email="otheruser@example.com", password="testpass")

    async def auth_communicator(self, user):
        # Helper to create an authenticated communicator
        communicator = WebsocketCommunicator(
            application=application,
            path="/ws/chat/",
        )
        # Force authentication in scope
        communicator.scope["user"] = user
        connected, _ = await communicator.connect()
        assert connected
        logger.info(f"User {user.id} connected.")
        return communicator

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self, user):
        communicator = await self.auth_communicator(user)
        await communicator.disconnect()
        logger.info(f"User {user.id} disconnected.")

    @pytest.mark.asyncio
    async def test_send_and_receive_message(self, user, user2):
        comm1 = await self.auth_communicator(user)
        comm2 = await self.auth_communicator(user2)

        # User1 sends a message to User2
        message = {
            "event": "send_message",
            "data": {
                "receiver_id": user2.id,
                "message": "Hello, User2!"
            }
        }
        await comm1.send_json_to(message)
        logger.info(f"User {user.id} sent message to User {user2.id}")

        # Both users should receive the message
        response1 = await comm1.receive_json_from()
        response2 = await comm2.receive_json_from()
        assert response1["event"] == "new_message"
        assert response2["event"] == "new_message"
        assert response1["data"]["message"] == "Hello, User2!"
        assert response2["data"]["message"] == "Hello, User2!"
        logger.info("Both users received the message.")

        await comm1.disconnect()
        await comm2.disconnect()

    @pytest.mark.asyncio
    async def test_mark_messages_read(self, user, user2, db):
        comm1 = await self.auth_communicator(user)
        comm2 = await self.auth_communicator(user2)

        # User1 sends a message to User2
        message = {
            "event": "send_message",
            "data": {
                "receiver_id": user2.id,
                "message": "Read this!"
            }
        }
        await comm1.send_json_to(message)
        response = await comm2.receive_json_from()
        message_id = response["data"]["message_id"]

        # User2 marks the message as read
        read_event = {
            "event": "read_confirmation",
            "data": {
                "message_ids": [message_id]
            }
        }
        await comm2.send_json_to(read_event)
        logger.info(f"User {user2.id} marked message {message_id} as read.")

        await comm1.disconnect()
        await comm2.disconnect()