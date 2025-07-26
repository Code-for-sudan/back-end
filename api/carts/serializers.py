from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for CartItem model with variation support"""
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.ImageField(source='product.picture', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    variation_key = serializers.CharField(read_only=True)
    
    class Meta:
        model = CartItem
        fields = [
            'id', 'product', 'product_name', 'product_price', 'product_image',
            'quantity', 'size', 'product_properties', 'subtotal', 
            'is_stock_reserved', 'variation_key', 'added_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_stock_reserved', 'added_at', 'updated_at']
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value
    
    def validate(self, data):
        # Check if size is required for this product
        if 'product' in data:
            product = data['product']
            size = data.get('size')
            
            if product.has_sizes and not size:
                raise serializers.ValidationError("Size must be specified for products with size variations")
            
            if not product.has_sizes and size:
                raise serializers.ValidationError("Size cannot be specified for products without size variations")
        
        return data


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart model"""
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_empty = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Cart
        fields = [
            'id', 'user', 'items', 'total_items', 'total_price', 
            'is_empty', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart with variation support"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    size = serializers.CharField(max_length=50, required=False, allow_blank=True)
    product_properties = serializers.JSONField(required=False)
    
    def validate_product_id(self, value):
        from products.models import Product
        try:
            product = Product.objects.get(id=value)
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")
    
    def validate(self, data):
        from products.models import Product
        
        # Get the product to validate size requirement
        try:
            product = Product.objects.get(id=data['product_id'])
            size = data.get('size')
            
            if product.has_sizes and not size:
                raise serializers.ValidationError("Size must be specified for products with size variations")
            
            if not product.has_sizes and size:
                raise serializers.ValidationError("Size cannot be specified for products without size variations")
                
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")
        
        return data


class CheckoutSingleItemSerializer(serializers.Serializer):
    """Serializer for single item checkout"""
    cart_item_id = serializers.IntegerField()
    shipping_address = serializers.CharField(max_length=255, required=False)
    payment_method = serializers.ChoiceField(
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
            ('cash_on_delivery', 'Cash on Delivery'),
            ('test_payment', 'Test Payment'),
        ],
        default='credit_card'
    )
    gateway_name = serializers.CharField(max_length=100, default='test_gateway')
    
    def validate_cart_item_id(self, value):
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("User authentication required")
            
        try:
            from .models import CartItem, Cart
            cart = Cart.objects.get(user=request.user)
            cart_item = CartItem.objects.get(id=value, cart=cart)
            return value
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            raise serializers.ValidationError("Cart item not found")


class CheckoutFullCartSerializer(serializers.Serializer):
    """Serializer for full cart checkout"""
    shipping_address = serializers.CharField(max_length=255, required=False)
    payment_method = serializers.ChoiceField(
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('bank_transfer', 'Bank Transfer'),
            ('mobile_money', 'Mobile Money'),
            ('cash_on_delivery', 'Cash on Delivery'),
            ('test_payment', 'Test Payment'),
        ],
        default='credit_card'
    )
    gateway_name = serializers.CharField(max_length=100, default='test_gateway')


class CartValidationSerializer(serializers.Serializer):
    """Serializer for cart validation before checkout"""
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Specific cart item IDs to validate. If not provided, validates entire cart."
    )


class CheckoutResponseSerializer(serializers.Serializer):
    """Serializer for checkout response"""
    checkout_type = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    order_count = serializers.IntegerField(read_only=True)
    payment_id = serializers.UUIDField(read_only=True)
    payment_hash = serializers.CharField(read_only=True)
    
    # For single item checkout
    order = serializers.JSONField(read_only=True)
    
    # For full cart checkout
    orders = serializers.JSONField(read_only=True)
