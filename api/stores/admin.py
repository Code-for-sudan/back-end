from django.contrib import admin
from .models import Store

@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'store_type', 'location', 'created_at')
    search_fields = ('name', 'location', 'store_type', 'description')
    list_filter = ('store_type', 'created_at', 'location')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': ('name', 'store_type', 'location')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
