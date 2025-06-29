from django.contrib import admin
from .models import Product

class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'product_name', 'category', 'price', 'quantity', 'store', 'owner_id'
    )
    search_fields = ('product_name', 'category', 'store__name')
    list_filter = ('category', 'store')

admin.site.register(Product, ProductAdmin)
