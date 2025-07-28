import json
import os
import logging
from rest_framework import serializers
from .models import Offer, Product, Tag, Size
from django.utils.dateparse import parse_datetime


class OfferSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    class Meta:
        model = Offer
        fields = [
            "id",
            "start_date",
            "end_date",
            "offer_price",
            "product",
            "is_active",
        ]
        required_fields = ["start_date", "end_date", "offer_price", "product"]
        read_only_fields = ["id", "is_active"]

    def to_internal_value(self, data):
        data = data.copy()
        data["start_date"] = parse_datetime(data["start_date"])
        data["end_date"] = parse_datetime(data["end_date"])
        return super().to_internal_value(data)

    def validate(self, data):
        """
        Validate start and end dates and ensure price is valid.
        """
        if data["offer_price"] <= 0:
            raise serializers.ValidationError(
                "Offer price must be greater than 0.")

        if data["start_date"] >= data["end_date"]:
            raise serializers.ValidationError(
                "Start date must be before end date.")
        if data['product'].price <= data['offer_price']:
            raise serializers.ValidationError(
                "Offer price must be less than the original product price.")
        return data


class SizeSerializer(serializers.ModelSerializer):
    logger = logging.getLogger(__name__)

    class Meta:
        model = Size
        fields = ["size", "available_quantity", "reserved_quantity"]
        extra_kwargs = {
            "available_quantity": {"required": True},
            # Always set to 0 during creation
            "reserved_quantity": {"read_only": True},
        }

    def validate_available_quantity(self, value):
        if value is not None and value < 0:
            self.logger.error("available_quantity cannot be negative.")
            raise serializers.ValidationError(
                "available_quantity cannot be negative.")
        return value

    def validate_reserved_quantity(self, value):
        if value is not None and value < 0:
            self.logger.error("reserved_quantity cannot be negative.")
            raise serializers.ValidationError(
                "reserved_quantity cannot be negative.")
        return value

    def create(self, validated_data):
        # Ensure reserved_quantity is always 0 for a new Size
        validated_data["reserved_quantity"] = 0
        return super().create(validated_data)


class ProductSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    sizes = SizeSerializer(many=True, required=False)
    offer = OfferSerializer(required=False, allow_null=True)
    logger = logging.getLogger(__name__)
    current_price = serializers.SerializerMethodField()

    def get_current_price(self, obj):
        return str(obj.current_price)

    class Meta:
        model = Product
        fields = [
            "id",
            "product_name",
            "product_description",
            "price",
            "current_price",
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
            "updated_at",
            "offer",
        ]
        read_only_fields = [
            "id",
            "owner_id",
            "store",
            "created_at",
            "updated_at",
            "reserved_quantity",
            'current_price',
            'is_deleted',
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
        if "offer" in data and isinstance(data["offer"], str):
            try:
                data["offer"] = json.loads(data["offer"])
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    {"offer": "Invalid JSON format for offer."})

        ret = super().to_internal_value(data)
        ret["sizes"] = data.get("sizes", [])
        ret["tags"] = data.get("tags", [])
        ret["offer"] = data.get("offer", None)
        return ret

    def validate_available_quantity(self, value):
        if value is not None and value < 0:
            self.logger.error("available_quantity cannot be negative.")
            raise serializers.ValidationError(
                "available_quantity cannot be negative.")
        return value

    def validate_reserved_quantity(self, value):
        if value is not None and value < 0:
            self.logger.error("reserved_quantity cannot be negative.")
            raise serializers.ValidationError(
                "reserved_quantity cannot be negative.")
        return value

    def validate_price(self, value):
        if value <= 0:
            self.logger.error("Price  cannot be negative.")
            raise serializers.ValidationError(
                "Price cannot be negative.")
        return value

    def validate(self, attrs):
        sizes = attrs.get("sizes", [])
        has_sizes = attrs.get("has_sizes")
        has_available = "available_quantity" in attrs
        # Validate sizes
        validated_sizes = SizeSerializer(many=True).run_validation(sizes)
        attrs["sizes"] = validated_sizes

        if has_sizes:
            if not validated_sizes and not self.partial:
                self.logger.error(
                    "At least one size must be provided when 'has_sizes' is True."
                )
                raise serializers.ValidationError(
                    "At least one size must be provided when 'has_sizes' is True."
                )
        else:
            if not has_available and not self.partial:
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
        offer_data = validated_data.pop("offer", None)
        tags_data = validated_data.pop("tags", [])
        sizes_data = validated_data.pop("sizes", [])
        if not validated_data.get("has_sizes"):
            validated_data["reserved_quantity"] = 0
        product = Product.objects.create(**validated_data)

        if offer_data:
            offer_data['product'] = product.id  # Attach product reference
            offer_serializer = OfferSerializer(data=offer_data)
            offer_serializer.is_valid(raise_exception=True)
            offer_serializer.save(product=product)

        for tag_name in tags_data:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            product.tags.add(tag)

        if sizes_data:
            for size_data in sizes_data:
                Size.objects.create(
                    product=product, reserved_quantity=0, **size_data)

        return product

    def validate_picture(self, image):
        if image is None:
            return image
        allowed_image_extensions = ["jpg", "jpeg", "png"]
        allowed_image_size = 5 * 1024 * 1024  # 5MB

        image_extension = os.path.splitext(image.name)[1][1:].lower()
        if image_extension not in allowed_image_extensions:
            self.logger.error(
                "Unsupported file extension. Allowed: jpg, jpeg, png.")
            raise serializers.ValidationError(
                "Unsupported file extension. Allowed: jpg, jpeg, png."
            )

        if image.size > allowed_image_size:
            self.logger.error("The image is too large. Max size: 5MB.")
            raise serializers.ValidationError(
                "The image is too large. Max size: 5MB.")
        return image

    def update(self, instance, validated_data):
        tags_data = validated_data.pop("tags", None)
        sizes_data = validated_data.pop("sizes", None)
        offer_data = validated_data.pop("offer", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.clear()
            for tag_name in tags_data:
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                instance.tags.add(tag)

        if sizes_data is not None:
            # Delete all existing sizes related to this product
            instance.sizes.all().delete()
            for size_data in sizes_data:
                Size.objects.create(
                    product=instance, reserved_quantity=0, **size_data)

        # Delete existing offer if it exists
        if offer_data is not None:
            if instance.offer:
                instance.offer.delete()
            # Create a new offer
            offer_data['product'] = instance.id
            offer_serializer = OfferSerializer(data=offer_data)
            offer_serializer.is_valid(raise_exception=True)
            offer_serializer.save(product=instance)
        return instance
