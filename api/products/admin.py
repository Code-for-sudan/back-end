# products/admin.py

from django.utils.html import mark_safe
from django.contrib import admin
from .models import (
    Category, Tag, Product, ProductHistory, Offer,
    Size
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["id", "name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = ["id", "name"]


class SizeInline(admin.TabularInline):
    model = Size
    extra = 0
    fields = ["size", "available_quantity", "reserved_quantity", "is_deleted"]
    readonly_fields = ["deleted_at"]
    can_delete = False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [SizeInline]
    list_display = [
        "id", "product_name", "category", "price",
        "available_quantity", "has_sizes", "is_deleted"
    ]
    list_filter = ["category", "has_sizes", "is_deleted"]
    search_fields = ["product_name", "brand", "category"]
    readonly_fields = ["created_at", "updated_at", "image_preview"]

    def get_fields(self, request, obj=None):
        fields = [field.name for field in self.model._meta.fields]
        if 'picture' in fields:
            fields.append("image_preview")
        return fields

    def image_preview(self, obj):
        if obj.picture:
            return mark_safe(f'<img src="{obj.picture.url}" width="150" height="150" />')
        return "No image"
    image_preview.short_description = "Picture"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("sizes")


@admin.register(ProductHistory)
class ProductHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "id", "product_name", "current_price", "store_name", "snapshot_taken_at"
    ]
    search_fields = ["product_name", "store_name", "owner_email"]
    readonly_fields = [
        field.name for field in ProductHistory._meta.fields
    ] + ["image_preview"]

    def get_fields(self, request, obj=None):
        fields = [field.name for field in self.model._meta.fields]
        if 'picture' in fields:
            fields.append("image_preview")
        return fields

    def image_preview(self, obj):
        if obj.picture:
            return mark_safe(f'<img src="{obj.picture.url}" width="150" height="150" />')
        return "No image"
    image_preview.short_description = "Picture"


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = [
        "product", "offer_price", "start_date", "end_date", "is_active"
    ]
    search_fields = ["product__product_name", "product__brand"]
    readonly_fields = ["created_at", "updated_at"]

    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = [
        "product", "size", "available_quantity", "reserved_quantity", "is_deleted"
    ]
    list_filter = ["is_deleted"]
    search_fields = ["product__product_name", "size"]
    readonly_fields = ["deleted_at"]
