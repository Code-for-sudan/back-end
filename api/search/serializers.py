from products.serializers import ProductSerializer

class ProductSearchSerializer(ProductSerializer):
    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields
        # depends on products serializer, customize as needed