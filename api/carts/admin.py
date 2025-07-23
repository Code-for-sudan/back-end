from django.contrib import admin
from .models import Cart, CartItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin configuration for Cart model"""
    list_display = ['user', 'total_items', 'total_price', 'created_at', 'updated_at']
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at', 'total_items', 'total_price']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user').prefetch_related('items')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """Admin configuration for CartItem model"""
    list_display = [
        'cart', 'product', 'quantity', 'subtotal', 'added_at'
    ]
    list_filter = ['added_at', 'updated_at']
    search_fields = ['cart__user__email', 'product__product_name']
    readonly_fields = ['added_at', 'updated_at', 'subtotal']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'cart__user', 'product'
        )
