from django.contrib import admin
from .models import EmailTemplate, EmailAttachment, EmailImage, EmailStyle

class EmailAttachmentInline(admin.TabularInline):
    model = EmailAttachment
    extra = 1

class EmailImageInline(admin.TabularInline):
    model = EmailImage
    extra = 1

class EmailStyleInline(admin.TabularInline):
    model = EmailStyle
    extra = 1

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'created_at', 'updated_at')
    search_fields = ('name', 'subject')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [EmailAttachmentInline, EmailImageInline, EmailStyleInline]
    fieldsets = (
        (None, {
            'fields': ('name', 'subject')
        }),
        ('Files', {
            'fields': ('html_file', 'plain_text_file')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ('template', 'file', 'created_at', 'updated_at')
    search_fields = ('template__name', 'file')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(EmailImage)
class EmailImageAdmin(admin.ModelAdmin):
    list_display = ('template', 'image', 'created_at', 'updated_at')
    search_fields = ('template__name', 'image')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(EmailStyle)
class EmailStyleAdmin(admin.ModelAdmin):
    list_display = ('template', 'style_file', 'created_at', 'updated_at')
    search_fields = ('template__name', 'style_file')
    list_filter = ('created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')
