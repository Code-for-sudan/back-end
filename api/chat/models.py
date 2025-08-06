from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatMessage(models.Model):
    """
    Model representing a chat message between users.
    
    Attributes:
        sender (ForeignKey): The user who sent the message.
        receiver (ForeignKey): The user who received the message.
        message (TextField): The content of the message.
        timestamp (DateTimeField): The time when the message was sent.
        is_read (BooleanField): Indicates whether the message has been read.
    Methods:
        get_message_preview(length=20): Returns a preview of the message content, truncated to the specified length. 
    """
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def get_message_preview(self, length=20):
        return self.message if len(self.message) <= length else self.message[:length] + '...'

    def __str__(self):
        return f'{self.sender} to {self.receiver}: {self.get_message_preview()}'
