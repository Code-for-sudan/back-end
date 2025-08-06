from rest_framework import serializers
from products.serializers import ProductSerializer


class ProductSearchSerializer(serializers.Serializer):
    results = ProductSerializer(many=True)
    page = serializers.IntegerField()
    total = serializers.IntegerField()
