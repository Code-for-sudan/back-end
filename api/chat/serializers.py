from rest_framework import serializers
from .models import ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = [
            "id", "sender_id", "receiver_id", "message",
            "timestamp", "is_read"
        ]
        read_only_fields = fields
