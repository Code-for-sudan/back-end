import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Product
from .serializers import ProductSerializer
from stores.models import Store

logger = logging.getLogger('products_views')

@extend_schema(
    request=ProductSerializer,
    responses={
        201: OpenApiResponse(
            response=ProductSerializer,
            description='Product created successfully.'
        ),
        400: OpenApiResponse(
            description='Product creation failed or validation error.'
        ),
    },
    description="Create, retrieve, update, or delete products. POST creates a new product associated with the authenticated user and their store.",
    summary="Product CRUD"
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    Handles product creation and retrieval.

    This viewset provides endpoints to:
        - List all products (GET /products), with optional filtering by category.
        - Create a new product (POST /products) associated with the authenticated user and their store.
        - Retrieve, update, or delete individual products (by ID) if needed.

    On creation, the viewset:
        - Validates the input data using the ProductSerializer.
        - Associates the new product with the authenticated user and their store.
        - Logs success and error events.
        - Returns a custom response with product details on success, or error details on failure.

    Args:
        request (Request): The HTTP request object containing product data.
    Returns:
        Response: A DRF Response object with a message, product data, and appropriate status code.
    """
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.all()  # Get all products initially

    def get_queryset(self):
        """Override to filter by category if specified."""
        queryset = self.queryset
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = self.request.user
            business_owner = getattr(user, 'business_owner_profile', None)
            store = business_owner.store if business_owner else None
            # Check if business_owner exists and store exists and is saved
            if not business_owner or not store or not getattr(store, 'pk', None):
                logger.error(f"Product creation failed: No store found for user {user.id}")
                return Response(
                    {"message": "No store found for this user."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            product = serializer.save(owner_id=user, store=store)
            logger.info(f"Product created successfully: Product ID {product.id} by User ID {user.id}")
            response_data = {
                "message": "Product created successfully",
                "product": {
                    "product_id": product.id,
                    "product_name": product.product_name,
                    "product_description": product.product_description,
                    "price": product.price,
                    "category": product.category,
                    "picture": product.picture,
                    "color": product.color,
                    "size": product.size,
                    "quantity": product.quantity,
                    "store_name": product.store_name,
                    "owner_id": str(product.owner_id.id),
                    "created_at": product.created_at,
                }
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Product creation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
