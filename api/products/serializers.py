from rest_framework import serializers
from .models import Product

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
        - picture (str): Required. URL to the product's image.
        - color (str): Optional. The color of the product.
        - size (str): Optional. The size of the product.
        - quantity (int): Required. The available quantity of the product.
        - owner_id (int): Read-only. The ID of the user who owns the product.
        - store_name (str): Read-only. The name of the store where the product is listed.
        - store_location (str): Read-only. The location of the store.
        - created_at (datetime): Read-only. Timestamp when the product was created.
    """

    store_name = serializers.ReadOnlyField()
    store_location = serializers.ReadOnlyField()
    owner_id = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'product_name',
            'product_description',
            'price',
            'category',
            'picture',
            'color',
            'size',
            'quantity',
            'owner_id',
            'store_name',
            'store_location',
            'created_at',
        ]
        read_only_fields = ['id', 'store_name', 'store_location', 'created_at', 'owner_id']
        extra_kwargs = {
            'product_name': {'required': True},
            'product_description': {'required': True},
            'price': {'required': True},
            'category': {'required': True},
            'picture': {'required': True},
            'quantity': {'required': True},
            'color': {'required': False, 'allow_null': True, 'allow_blank': True},
            'size': {'required': False, 'allow_null': True, 'allow_blank': True},
        }