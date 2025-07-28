import json
import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Product, Size, Tag
from .serializers import ProductSerializer
from stores.models import Store
from django.utils.timezone import now
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

    def get_permissions(self):
        # Allow unauthenticated access for list and retrieve actions
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    queryset = Product.objects.alive()

    def get_queryset(self):
        """Override to filter by category and optionally sort by price, recent, or both. Only alive products."""
        queryset = self.queryset
        category = self.request.query_params.get("category")
        sort = self.request.query_params.get("sort")

        if category:
            queryset = queryset.filter(category=category)
        has_offer = self.request.query_params.get("has_offer")
        if has_offer and has_offer.lower() == "true":
            queryset = queryset.filter(
                offer__start_date__lte=now(),
                offer__end_date__gte=now()
            )
        # sort param can be: 'recent', 'price', '-price', 'price,-created_at', etc. (comma-separated list)
        if sort:
            field_map = {
                "recent": "-created_at",
                "-recent": "created_at",
                "price": "current_price",
                "-price": "-current_price",
            }
            valid_fields = set(
                f.name for f in Product._meta.get_fields() if hasattr(f, 'attname'))
            sort_fields = []
            for field in sort.split(","):
                field = field.strip()
                mapped = field_map.get(field)
                if mapped:
                    sort_fields.append(mapped)
                elif field.lstrip("-") in valid_fields:
                    sort_fields.append(field)
                # else: ignore unknown fields
            if sort_fields:
                queryset = queryset.order_by(*sort_fields)

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

        user = self.request.user
        business_owner = getattr(user, "business_owner_profile", None)
        store = business_owner.store if business_owner else None

        if not business_owner or not store:
            return Response(
                {"message": "No store found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            logger.error(f"Product creation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        product = serializer.save(owner_id=user, store=store)
        logger.info(
            f"Product created successfully: {product.id} by user {user.id}")
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
            product = self.get_queryset().prefetch_related(
                "sizes").get(pk=kwargs["pk"])
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)

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
        product.delete()
        logger.info(
            f"Product {product.id} soft-deleted by user {request.user.id}")
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        product = self.get_object()
        data = request.data.copy()
        serializer = self.get_serializer(product, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_product = serializer.save()
        if product.owner_id != request.user:
            logger.critical(
                "User %s attempted to update product %s without permission.",
                request.user.id,
                product.id,
            )
            return Response(
                {"detail": "You do not have permission to update this product."},
                status=status.HTTP_403_FORBIDDEN,
            )
        logger.info(
            f"Product {updated_product.id} updated by user {request.user.id}")
        response = {
            "message": "Product updated successfully",
            "product": ProductSerializer(updated_product).data,
        }
        return Response(response, status=status.HTTP_200_OK)
