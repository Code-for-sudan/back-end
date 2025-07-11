from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """
    Admin configuration for ChatMessage model.
    Displays sender, receiver, message preview, timestamp, and read status.
    Allows filtering by sender, receiver, and read status.
    """
    list_display = ("id", "sender", "receiver", "get_message_preview", "timestamp", "is_read")
    list_filter = ("sender", "receiver", "is_read")
    search_fields = ("sender__email", "receiver__email", "message")
    readonly_fields = ("timestamp",)

    def get_message_preview(self, obj):
        return obj.get_message_preview(40)
    get_message_preview.short_description = "Message Preview"