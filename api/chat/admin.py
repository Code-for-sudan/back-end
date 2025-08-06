from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """
    Admin configuration for ChatMessage model.
    Displays all relevant fields and provides filtering, searching, and read-only timestamp.
    """
    list_display = ("id", "sender", "receiver", "get_message_preview", "timestamp", "is_read")
    list_filter = ("sender", "receiver", "is_read", "timestamp")
    search_fields = ("sender__email", "receiver__email", "message")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)
    fieldsets = (
        (None, {
            'fields': ("sender", "receiver", "message", "is_read")
        }),
        ("Timestamps", {
            'fields': ("timestamp",)
        }),
    )

    def get_message_preview(self, obj):
        return obj.get_message_preview(40)
    get_message_preview.short_description = "Message Preview"
