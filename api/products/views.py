import json
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Product, Size, Tag
from .serializers import ProductSerializer
from stores.models import Store

logger = logging.getLogger("products_views")


@extend_schema(
    description="Product CRUD operations. Supports listing, creating, retrieving, updating, and deleting products.",
    summary="Product CRUD",
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
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)
        return queryset

    @extend_schema(
        request=ProductSerializer,
        responses={
            201: OpenApiResponse(
                response=ProductSerializer, description="Product created successfully."
            ),
            400: OpenApiResponse(
                description="Product creation failed or validation error."
            ),
        },
        summary="Create Product",
    )
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            logger.error(f"Product creation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = self.request.user
        business_owner = getattr(user, "business_owner_profile", None)
        store = business_owner.store if business_owner else None

        if not business_owner or not store:
            return Response(
                {"message": "No store found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        product = serializer.save(owner_id=user, store=store)
        logger.info(f"Product created successfully: {product.id} by user {user.id}")
        response = {
            "message": "Product created successfully",
            "product": ProductSerializer(product).data,
        }
        return Response(response, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=ProductSerializer,
                description="Product retrieved successfully.",
            ),
            404: OpenApiResponse(description="Product not found."),
        },
        summary="Retrieve Product",
    )

    def retrieve(self, request, *args, **kwargs):
        try:
            product = self.get_queryset().prefetch_related("sizes").get(pk=kwargs["pk"])
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=ProductSerializer,
        responses={
            200: OpenApiResponse(
                response=ProductSerializer, description="Product updated successfully."
            ),
            400: OpenApiResponse(
                description="Product update failed or validation error."
            ),
            404: OpenApiResponse(description="Product not found."),
        },
        summary="Update Product",
    )
    @extend_schema(
        responses={
            204: OpenApiResponse(description="Product deleted successfully."),
            403: OpenApiResponse(
                description="You do not have permission to delete this product."
            ),
            404: OpenApiResponse(description="Product not found."),
        },
        summary="Delete Product",
    )

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        # Check if the current user is the owner
        if product.owner_id != request.user:
            logger.critical(
                "User %s attempted to delete product %s without permission.",
                request.user.id,
                product.id,
            )
            return Response(
                {"detail": "You do not have permission to delete this product."},
                status=status.HTTP_403_FORBIDDEN,
            )
        product.picture.delete(save=False)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT,
        )
