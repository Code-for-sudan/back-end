from rest_framework import serializers
from .models import ChatMessage
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for the ChatMessage model.
    
    Fields:
        - id (int): Unique identifier for the chat message.
        - sender (User): The user who sent the message.
        - receiver (User): The user who received the message.
        - message (str): The content of the chat message.
        - timestamp (datetime): The time when the message was sent.
        - is_read (bool): Indicates whether the message has been read by the receiver.
    Methods:
        - validate(data): Validates that the sender and receiver are not the same user.
        - validate_message(value): Validates the message content, ensuring it is not empty and does not exceed 1000 characters.
    """
    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'sender',
            'receiver',
            'message',
            'timestamp',
            'is_read',
        ]
        read_only_fields = ['id', 'timestamp']

    def validate(self, data):
        sender = data.get('sender')
        receiver = data.get('receiver')

        if sender == receiver:
            raise serializers.ValidationError("Sender and receiver cannot be the same user.")

        return data

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty or whitespace.")
        if len(value) > 1000:
            raise serializers.ValidationError("Message is too long (max 1000 characters).")
        return value

class ChatHistorySerializer(serializers.Serializer):
    """
    Serializer for validation of chat history requests.
    """
    customer_id = serializers.IntegerField(required=True)

    def validate_customer_id(self, value):
        try:
            customer = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Customer not found.")
        return value
    
class ChatContactsSerializer(serializers.Serializer):
    contact_id = serializers.IntegerField()
    contact_name = serializers.CharField()
    contact_img = serializers.CharField(allow_null=True)
    last_message = serializers.CharField()
    timestamp = serializers.DateTimeField()
    unread_count = serializers.IntegerField()
    online = serializers.BooleanField()
    last_seen = serializers.DateTimeField(allow_null=True)