from datetime import datetime, timezone
from functools import cache
import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatMessage

User = get_user_model()
online_users = set()
logger = logging.getLogger("chat_consumers")

class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    ChatConsumer handles real-time chat functionality over WebSockets.

    Features:
    - Authenticates users on connection (only allows authenticated users).
    - Adds/removes users to/from a personal group for targeted messaging.
    - Tracks user online/offline status and broadcasts status updates.
    - Handles sending and receiving chat messages between users.
    - Marks messages as read when confirmed by the client.
    - Uses Django Channels groups for efficient message delivery.
    - Stores chat messages in the database asynchronously.

    Events handled:
    - "send_message": Sends a message from the sender to the receiver and notifies both.
    - "user_status": Broadcasts the user's online/offline status.
    - "read_confirmation": Marks specified messages as read.

    All communication is in JSON format.
    """

    async def connect(self):
        self.user = self.scope["user"]
        try:
            if self.user.is_authenticated:
                await self.accept()
                await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)
                logger.info(f"User {self.user.id} connected to chat.")
                # Save as online (via Redis or cache)
                await self.set_user_online(self.user.id)
            else:
                logger.warning("Anonymous user tried to connect to chat.")
                await self.close()
        except Exception as e:
            logger.error(f"Error during connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if self.user.is_authenticated:
                await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)
                logger.info(f"User {self.user.id} disconnected from chat.")
                await self.set_user_offline(self.user.id)
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def receive_json(self, content):
        try:
            event = content.get("event")
            data = content.get("data")
            logger.debug(f"Received event: {event} with data: {data} from user {getattr(self.user, 'id', None)}")

            if event == "send_message":
                receiver_id = data.get("receiver_id")
                message_text = data.get("message")
                message = await self.create_message(self.user.id, receiver_id, message_text)

                response = {
                    "event": "new_message",
                    "data": {
                        "message_id": message.id,
                        "sender_id": message.sender_id,
                        "receiver_id": message.receiver_id,
                        "temp_id": getattr(message, "temp_id", None),
                        "message": message.message,
                        "timestamp": message.timestamp.isoformat(),
                        "status": "sent",
                        "is_read": False,
                    }
                }

                # Send to receiver and sender groups
                await self.channel_layer.group_send(
                    f"user_{receiver_id}", {"type": "chat.message", "message": response}
                )
                await self.channel_layer.group_send(
                    f"user_{self.user.id}", {"type": "chat.message", "message": response}
                )
                logger.info(f"User {self.user.id} sent message to user {receiver_id}")

            elif event == "user_status":
                await self.broadcast_status(data)

            elif event == "read_confirmation":
                message_ids = data.get("message_ids", [])
                await self.mark_messages_read(message_ids)
                logger.info(f"User {self.user.id} marked messages as read: {message_ids}")

            else:
                logger.warning(f"Unknown event type: {event}")
                await self.send_json({"event": "error", "data": {"message": "Unknown event type."}})
        except Exception as e:
            logger.error(f"Error in receive_json: {e}")
            await self.send_json({"event": "error", "data": {"message": str(e)}})

    async def chat_message(self, event):
        try:
            await self.send_json(event["message"])
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")

    @database_sync_to_async
    def create_message(self, sender_id, receiver_id, message_text):
        try:
            sender = User.objects.get(id=sender_id)
            receiver = User.objects.get(id=receiver_id)
            return ChatMessage.objects.create(sender=sender, receiver=receiver, message=message_text)
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise

    async def set_user_online(self, user_id):
        try:
            cache.set(f"user_online_{user_id}", True, timeout=300)  # expires in 5 mins
            await self.channel_layer.group_send(
                f"user_{user_id}",
                {
                    "type": "chat.message",
                    "message": {
                        "event": "user_status",
                        "data": {
                            "user_id": user_id,
                            "online": True,
                            "last_seen": None
                        }
                    }
                }
            )
            logger.info(f"User {user_id} set as online.")
        except Exception as e:
            logger.error(f"Error setting user online: {e}")

    async def set_user_offline(self, user_id):
        try:
            last_seen = timezone.now().isoformat()
            cache.set(f"user_online_{user_id}", False)
            cache.set(f"user_last_seen_{user_id}", last_seen)

            await self.channel_layer.group_send(
                f"user_{user_id}",
                {
                    "type": "chat.message",
                    "message": {
                        "event": "user_status",
                        "data": {
                            "user_id": user_id,
                            "online": False,
                            "last_seen": last_seen
                        }
                    }
                }
            )
            logger.info(f"User {user_id} set as offline.")
        except Exception as e:
            logger.error(f"Error setting user offline: {e}")

    async def broadcast_status(self, data):
        try:
            user_id = data.get("user_id")
            status_data = {
                "event": "user_status",
                "data": {
                    "user_id": user_id,
                    "online": data.get("online"),
                    "last_seen": data.get("last_seen"),
                }
            }
            await self.channel_layer.group_send(
                f"user_{user_id}",
                {"type": "chat.message", "message": status_data}
            )
            logger.info(f"Broadcasted status for user {user_id}: {status_data['data']}")
        except Exception as e:
            logger.error(f"Error broadcasting status: {e}")

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        try:
            ChatMessage.objects.filter(id__in=message_ids).update(is_read=True)
        except Exception as e:
            logger.error(f"Error marking messages as read: {e}")

