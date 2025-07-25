import json
import os
import logging
from rest_framework import serializers
from .models import Product, Tag, Size


class SizeSerializer(serializers.ModelSerializer):
    logger = logging.getLogger(__name__)

    class Meta:
        model = Size
        fields = ["size", "available_quantity", "reserved_quantity"]
        extra_kwargs = {
            "available_quantity": {"required": True},
            "reserved_quantity": {"read_only": True},  # Always set to 0 during creation
        }

    def create(self, validated_data):
        # Ensure reserved_quantity is always 0 for a new Size
        validated_data["reserved_quantity"] = 0
        return super().create(validated_data)


class ProductSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    sizes = SizeSerializer(many=True, required=False)
    logger = logging.getLogger(__name__)

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
            "sizes",
            "owner_id",
            "store",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "owner_id",
            "store",
            "created_at",
        ]
        extra_kwargs = {
            "product_name": {"required": True},
            "product_description": {"required": True},
            "price": {"required": True},
            "category": {"required": True},
            "picture": {"required": True},
            "has_sizes": {"required": True},
            "store": {"required": True},
        }

    def get_tags(self, obj):
        # Return list of tag names for the product
        return [tag.name for tag in obj.tags.all()]

    def to_internal_value(self, data):
        data = data.copy()
        if "sizes" in data and isinstance(data["sizes"], str):
            try:
                data["sizes"] = json.loads(data["sizes"])
            except json.JSONDecodeError:
                raise serializers.ValidationError({"sizes": "Invalid JSON."})
        # Convert tags from string to list if it's a JSON string
        if "tags" in data and isinstance(data["tags"], str):
            try:
                data["tags"] = json.loads(data["tags"])
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    {"tags": "Invalid JSON format for tags."}
                )

        ret = super().to_internal_value(data)
        ret["sizes"] = data.get("sizes", [])
        ret["tags"] = data.get("tags", [])
        return ret

    def validate(self, attrs):
        sizes = attrs.get("sizes", [])
        has_sizes = attrs.get("has_sizes")
        has_available = "available_quantity" in attrs

        # Validate sizes
        validated_sizes = SizeSerializer(many=True).run_validation(sizes)
        attrs["sizes"] = validated_sizes

        if has_sizes:
            if not validated_sizes:
                self.logger.error(
                    "At least one size must be provided when 'has_sizes' is True."
                )
                raise serializers.ValidationError(
                    "At least one size must be provided when 'has_sizes' is True."
                )
        else:
            if not has_available:
                self.logger.error(
                    "Product must have 'available_quantity' when has_sizes is False."
                )
                raise serializers.ValidationError(
                    "Product must have 'available_quantity' when has_sizes is False."
                )
        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["tags"] = [tag.name for tag in instance.tags.all()]
        return rep

    def create(self, validated_data):
        tags_data = validated_data.pop("tags", [])
        sizes_data = validated_data.pop("sizes", [])
        if not validated_data.get("has_sizes"):
            validated_data["reserved_quantity"] = 0
        product = Product.objects.create(**validated_data)

        for tag_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            product.tags.add(tag)

        if sizes_data:
            for size_data in sizes_data:
                Size.objects.create(product=product, reserved_quantity=0, **size_data)

        return product

    def validate_picture(self, image):
        if image is None:
            return image
        allowed_image_extensions = ["jpg", "jpeg", "png"]
        allowed_image_size = 5 * 1024 * 1024  # 5MB

        image_extension = os.path.splitext(image.name)[1][1:].lower()
        if image_extension not in allowed_image_extensions:
            self.logger.error("Unsupported file extension. Allowed: jpg, jpeg, png.")
            raise serializers.ValidationError(
                "Unsupported file extension. Allowed: jpg, jpeg, png."
            )

        if image.size > allowed_image_size:
            self.logger.error("The image is too large. Max size: 5MB.")
            raise serializers.ValidationError("The image is too large. Max size: 5MB.")
        return image
