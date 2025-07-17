from django.contrib import admin
from .models import Product

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'product_name', 'category', 'price', 'quantity', 'color', 'size',
        'store', 'store_name', 'store_location', 'owner_id', 'created_at'
    )
    search_fields = (
        'product_name', 'category', 'store__name', 'store__location', 'owner_id__email'
    )
    list_filter = ('category', 'store', 'color', 'size', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    fieldsets = (
        (None, {
            'fields': (
                'product_name', 'product_description', 'price', 'category', 'picture',
                'color', 'size', 'quantity', 'owner_id', 'store'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
