import logging
import os
from rest_framework import serializers
from .models import Product, Size, Tag

logger = logging.getLogger("product_serializer")

class TagListSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError("Expected a list of tag names.")
        tags = []
        for item in data:
            if not isinstance(item, str):
                raise serializers.ValidationError("Each tag must be a string.")
            name = item.strip()
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        return tags

    def to_representation(self, value):
        return [{"id": tag.id, "name": tag.name} for tag in value]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]
        read_only_fields = ["id"]
        list_serializer_class = TagListSerializer


class SizeSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product'
    )

    class Meta:
        model = Size
        fields = [
            'id',
            'product_id',
            'size',
            'available_quantity',
            'reserved_quantity',
        ]
        read_only_fields = ['id']

class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model.
    Handles serialization and deserialization of product data, including validation for required and optional fields.
    Fields:
        - id (int): Read-only. The unique identifier for the product.
        - product_name (str): Required. The name of the product.
        - product_description (str): Required. Detailed description of the product.
        - price (decimal): Required. The price of the product.
        - category (str): Required. The category of the product.
        - picture (str): Required. The product's image.
        - color (str): Optional. The color of the product.
        - size (str): Optional. The size of the product.
        - quantity (int): Required. The available quantity of the product.
        - owner_id (int): Read-only. The ID of the user who owns the product.
        - store_name (str): Read-only. The name of the store where the product is listed.
        - store_location (str): Read-only. The location of the store.
        - created_at (datetime): Read-only. Timestamp when the product was created.
    """

    picture = serializers.ImageField()
    store_name = serializers.ReadOnlyField(source="store.name")
    store_location = serializers.ReadOnlyField(source="store.location")
    owner_id = serializers.PrimaryKeyRelatedField(read_only=True)
    category = serializers.CharField(max_length=100)
    tags = TagSerializer(many=True, required=False)
    sizes = SizeSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id",
            "product_name",
            "product_description",
            "price",
            "brand",
            "category",
            "picture",
            "color",
            "available_quantity",
            "reserved_quantity",
            "has_sizes",
            "properties",
            "tags",
            "owner_id",
            "store_name",
            "store_location",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "store_name",
            "store_location",
            "created_at",
            "owner_id",
        ]
        extra_kwargs = {
            "product_name": {"required": True},
            "product_description": {"required": True},
            "price": {"required": True},
            "brand": {"required": False, "allow_null": True, "allow_blank": True},
            "category": {"required": True},
            "picture": {"required": True},
            "available_quantity": {"required": True},
            "color": {"required": False, "allow_null": True, "allow_blank": True},
            "reserved_quantity": {"required": False, "allow_null": True},
            "has_sizes": {"required": True},
            "properties": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        has_sizes = attrs.get("has_sizes")
        reserved_quantity = attrs.get("reserved_quantity")
        available_quantity = attrs.get("available_quantity")
        sizes = self.initial_data.get("sizes")

        if has_sizes:
            if not sizes or len(sizes) == 0:
                raise serializers.ValidationError(
                    {
                        "sizes": "At least one size entry is required when has_sizes is True."
                    }
                )
            if reserved_quantity is not None:
                raise serializers.ValidationError(
                    {
                        "reserved_quantity": "This field must be null when has_sizes is True."
                    }
                )
            if available_quantity is not None:
                raise serializers.ValidationError(
                    {
                        "available_quantity": "This field must be null when has_sizes is True."
                    }
                )
        else:
            if sizes:
                raise serializers.ValidationError(
                    {"sizes": "Sizes must be empty when has_sizes is False."}
                )
            if reserved_quantity is None:
                raise serializers.ValidationError(
                    {
                        "reserved_quantity": "This field cannot be null when has_sizes is False."
                    }
                )
            if available_quantity is None:
                raise serializers.ValidationError(
                    {
                        "available_quantity": "This field cannot be null when has_sizes is False."
                    }
                )

        return attrs

    def validate_category(self, value):
        if not value:
            raise serializers.ValidationError("Category is required.")
        if not isinstance(value, str):
            raise serializers.ValidationError("Category must be a string.")
        return value.strip()

    def validate_tags(self, value):
        # Normalize each tag string
        return [tag.strip() for tag in value]

    def validate_picture(self, image):
        if image is None:
            return image
        allowed_image_extensions = ["jpg", "jpeg", "png"]
        allowed_image_size = 5 * 1024 * 1024  # 5MB

        image_extension = os.path.splitext(image.name)[1][1:].lower()
        if image_extension not in allowed_image_extensions:
            logger.error("Unsupported file extension. Allowed: jpg, jpeg, png.")
            raise serializers.ValidationError(
                "Unsupported file extension. Allowed: jpg, jpeg, png."
            )

        if image.size > allowed_image_size:
            logger.error("The image is too large. Max size: 5MB.")
            raise serializers.ValidationError("The image is too large. Max size: 5MB.")
        return image

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Category is now a string
        data["category"] = instance.category
        # Convert tags to list of strings
        data["tags"] = [tag["name"] for tag in data.get("tags", [])]
        return data



