from datetime import datetime
from functools import cache
import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatMessage

User = get_user_model()
online_users = set()

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            await self.accept()
            await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)
            # Save as online (via Redis or cache)
            await self.set_user_online(self.user.id)
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)
            await self.set_user_offline(self.user.id)

    async def receive_json(self, content):
        event = content.get("event")
        data = content.get("data")

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
                    "message": message.message,
                    "timestamp": message.timestamp.isoformat(),
                    "status": "sent"
                }
            }

            # Send to receiver and sender groups
            await self.channel_layer.group_send(
                f"user_{receiver_id}", {"type": "chat.message", "message": response}
            )
            await self.channel_layer.group_send(
                f"user_{self.user.id}", {"type": "chat.message", "message": response}
            )

        elif event == "user_status":
            await self.broadcast_status(data)

        elif event == "mark_read":
            message_ids = data.get("message_ids", [])
            await self.mark_messages_read(message_ids)


    async def chat_message(self, event):
        await self.send_json(event["message"])

    @database_sync_to_async
    def create_message(self, sender_id, receiver_id, message_text):
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        return ChatMessage.objects.create(sender=sender, receiver=receiver, message=message_text)

    async def set_user_online(self, user_id):
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

    async def set_user_offline(self, user_id):
        last_seen = datetime.datetime.utcnow().isoformat()
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

    async def broadcast_status(self, data):
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

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        ChatMessage.objects.filter(id__in=message_ids).update(is_read=True)

