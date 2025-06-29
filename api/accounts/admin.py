from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, BusinessOwner


class CustomUserAdmin(UserAdmin):
    """
    CustomUserAdmin is a custom admin class for managing user models in the Django admin interface.
    Attributes:
        list_display (tuple): Fields to display in the list view of the admin.
        search_fields (tuple): Fields to include in the search functionality.
        ordering (tuple): Default ordering for the list view.
        fieldsets (tuple): Fieldsets for organizing fields in the detail view.
        add_fieldsets (tuple): Fieldsets for organizing fields in the add user form.
    """
    
    list_display = (
        'email', 'first_name', 'last_name',
        'is_staff', 'profile_picture', 'phone_number',
        'whatsapp_number', 'gender', 'location'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'profile_picture', 'location')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'location')}
        ),
    )


class BussinessUserAdmin(admin.ModelAdmin):
    search_fields = ('user__email', 'store__name')
    list_display = ('user', 'store')
    search_fields = ('user__email', 'store__name')


# Register the custom user model with the custom admin class
admin.site.register(User, CustomUserAdmin)
admin.site.register(BusinessOwner, BussinessUserAdmin)
