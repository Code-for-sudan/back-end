from django.contrib import admin
from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model"""
    list_display = [
        'order_id', 'user_id', 'product', 'quantity', 'total_price', 
        'status', 'payment_status', 'created_at'
    ]
    list_filter = [
        'status', 'payment_status', 'payment_method', 
        'created_at', 'updated_at'
    ]
    search_fields = [
        'order_id', 'user_id__email', 'product__product_name', 
        'payment_hash'
    ]
    readonly_fields = [
        'order_id', 'payment_hash', 'payment_key', 'created_at', 
        'updated_at', 'paid_at'
    ]
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'user_id', 'status', 'created_at', 'updated_at')
        }),
        ('Product Details', {
            'fields': ('product', 'product_variation', 'quantity', 'unit_price', 'total_price')
        }),
        ('Address Information', {
            'fields': ('shipping_address',)
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'payment_hash', 
                      'payment_key', 'payment_amount', 'paid_at')
        }),
        ('Notes', {
            'fields': ('customer_notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user_id', 'product', 'product__store'
        )
