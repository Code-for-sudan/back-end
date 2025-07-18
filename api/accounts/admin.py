from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, BusinessOwner

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Custom admin for the User model, exposing all fields and organizing them for easy management.
    """
    list_display = (
        'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser',
        'account_type', 'phone_number', 'whatsapp_number', 'gender', 'location',
        'profile_picture', 'total_spent', 'is_store_owner', 's_subscribed', 'created_at', 'updated_at'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'account_type', 'gender', 'is_store_owner', 's_subscribed', 'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone_number', 'whatsapp_number', 'location')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'profile_picture', 'phone_number', 'whatsapp_number',
                'gender', 'location', 'account_type', 'total_spent', 'is_store_owner', 's_subscribed'
            )
        }),
        ('OTP Info', {'fields': ('otp', 'otp_expires_at')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'password1', 'password2',
                'profile_picture', 'phone_number', 'whatsapp_number', 'gender', 'location',
                'account_type', 'is_store_owner', 's_subscribed', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
            ),
        }),
    )

@admin.register(BusinessOwner)
class BusinessOwnerAdmin(admin.ModelAdmin):
    list_display = ('user', 'store')
    search_fields = ('user__email', 'store__name')
