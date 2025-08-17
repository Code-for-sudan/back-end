import logging
from typing import Literal
from rest_framework.decorators import action
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from products.models import Offer, Product, Size
from products.serializers import ProductSerializer
from django.utils.timezone import now
from django.db.models import Case, When, F, DecimalField, Q
logger = logging.getLogger("products_views")


@extend_schema(
    description="""
    Product CRUD operations.

    - **GET /products/**: List products (supports filters and sorting)
    - **POST /products/**: Create a new product (authenticated only)
    - **GET /products/{id}/**: Retrieve product with optional favourite info
    - **PATCH /products/{id}/**: Update product (authenticated owner only)
    - **DELETE /products/{id}/**: Delete product (soft delete by owner)
    """,
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
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_permissions(self):
        # Allow unauthenticated access for list and retrieve actions
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    queryset = Product.objects.all()
    query_parameters = [
        OpenApiParameter(
            name="category", required=False,
            type=str, description="Filter by category name"),
        OpenApiParameter(
            name="classification", required=False,
            type=str, description="Filter by classification"),
        OpenApiParameter(
            name="has_offer", required=False, type=bool,
            description="Filter by active offer (true only)"),
        OpenApiParameter(
            name="sort", required=False, type=str,
            description="Sort by fields like `price`, `-price`, `recent`, etc. (comma-separated fields, e.g. `-price,created_at`)"),
        OpenApiParameter(name='store', description="Filter by store id"),
        OpenApiParameter(name="availability",
                         required=False, type=str,
                         enum=["available", "partially_available", "unavailable"],
                         description="Filter by availability status. Can be repeated for multiple values (e.g. `?availability=available&availability=partially_available`)"),
    ]

    def get_queryset(self):
        """Override to filter by category and optionally sort by price, recent, or both. Only alive products."""
        queryset = self.queryset.select_related(
            'offer').prefetch_related('sizes')
        category = self.request.query_params.get("category")
        classification = self.request.query_params.get("classification")
        store_id = self.request.query_params.get("store")
        has_offer = self.request.query_params.get("has_offer")
        sort = self.request.query_params.get("sort")
        availability = self.request.query_params.getlist("availability")

        if availability:
            availability_q = Q()
            base_qs = Product.objects.only("pk")
            if "available" in availability:
                availability_q |= Q(pk__in=base_qs.available())
            if "partially_available" in availability:
                availability_q |= Q(pk__in=base_qs.partially_available())
            if "unavailable" in availability:
                availability_q |= Q(pk__in=base_qs.unavailable())

            queryset = queryset.filter(availability_q)

        if category:
            queryset = queryset.filter(category=category)

        if classification:
            queryset = queryset.filter(classification=classification)

        if store_id:
            queryset = queryset.filter(store=store_id)

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
                "price": "current_price_",
                "-price": "-current_price_",
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
                if 'current_price_' in sort_fields or '-current_price_' in sort_fields:
                    queryset = queryset.annotate(
                        current_price_=Case(
                            When(
                                offer__start_date__lte=now(),
                                offer__end_date__gte=now(),
                                then=F("offer__offer_price")
                            ),
                            default=F("price"),
                            output_field=DecimalField()
                        )
                    )
                queryset = queryset.order_by(*sort_fields)

        return queryset

    @extend_schema(
        request=ProductSerializer,
        responses={
            201: OpenApiResponse(ProductSerializer, description="Product created successfully."),
            400: OpenApiResponse(description="Validation error or user has no store."),
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
            200: OpenApiResponse(ProductSerializer, description="Product retrieved successfully."),
            404: OpenApiResponse(description="Product not found."),
        },
        summary="Retrieve Product",
        description="Retrieve a single product by ID. Adds `is_favourite` if user is authenticated.",
    )
    def retrieve(self, request, *args, **kwargs):
        try:
            product = self.get_queryset().get(pk=kwargs["pk"])
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."},
                            status=status.HTTP_404_NOT_FOUND)

        product_data = ProductSerializer(product).data
        if request.user.is_authenticated:
            product_data["is_favourite"] = request.user.favourite_products.filter(
                pk=product.pk
            ).exists()
        else:
            product_data["is_favourite"] = False

        return Response(product_data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Product deleted successfully."),
            403: OpenApiResponse(description="You do not have permission to delete this product."),
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

    @extend_schema(
        request=ProductSerializer,
        responses={
            200: OpenApiResponse(ProductSerializer, description="Product updated successfully."),
            403: OpenApiResponse(description="User does not own the product."),
            400: OpenApiResponse(description="Validation error."),
        },
        summary="Update Product",
    )
    def update(self, request, *args, **kwargs):
        product = self.get_object()
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
        data = request.data.copy()
        serializer = self.get_serializer(product, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_product = serializer.save()
        logger.info(
            f"Product {updated_product.id} updated by user {request.user.id}")
        response = {
            "message": "Product updated successfully",
            "product": ProductSerializer(updated_product).data,
        }
        return Response(response, status=status.HTTP_200_OK)

    @extend_schema(
        responses={200: ProductSerializer(many=True)},
        summary="List Products",
        description="""
        Get all products with support for:

        - **category**: Filter by category name
        - **classification**: Filter by classification
        - **store**: Filter by store id
        - **has_offer**: Filter by active offers (true/false)
        - **sort**: Sort results (comma-separated fields, e.g. `-price,created_at`)
        - **availability**: Filter by availability status. Can be repeated for multiple values (e.g. `?availability=available&availability=partially_available`)
        - **is_favourite**: Added to each product if user is authenticated
        """,
        parameters=query_parameters
    )
    def list(self, request, *args, **kwargs):
        products = self.get_queryset()
        # Apply DRF pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serialized_products = ProductSerializer(page, many=True).data
        else:
            serialized_products = ProductSerializer(products, many=True).data

        if request.user.is_authenticated:
            favourite_ids = set(
                request.user.favourite_products.values_list("id", flat=True)
            )
            for product_data in serialized_products:
                product_data["is_favourite"] = product_data["id"] in favourite_ids
        else:
            for product_data in serialized_products:
                product_data["is_favourite"] = False

        if page is not None:
            return self.get_paginated_response(serialized_products)

        return Response(serialized_products, status=status.HTTP_200_OK)

    @extend_schema(
        summary="List authenticated user's products",
        description="Returns a paginated list of products that belong to the authenticated seller's store. "
                    "Includes support for filtering, searching, and ordering like the list products endpoint.",
        responses={
            200: OpenApiResponse(description="List of products owned by the authenticated seller."),
            403: OpenApiResponse(description="This user is not a seller."),
        },

        parameters=query_parameters,
        tags=["products"]
    )
    @action(detail=False, methods=["get"], url_path="my-products", url_name="my-products")
    def my_products(self, request):
        user = request.user
        if not user.account_type == 'seller':
            return Response({"detail": "This user is not a seller."}, status=403)
        qs = self.get_queryset().filter(owner_id=user.id)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DeleteProductSizeView(APIView):
    """
    Deletes a size of a specific product by product_id and size_id.
    Only the product owner can perform this action.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Delete Product Size",
        description="""
        Deletes a size from a product.

        - Only the **product owner** can perform this action.
        - Fails if:
            - The size does not exist for the product.
            - The size is the only one available for a product with sizes.
            - The size has a non-zero reserved quantity.
        """,
        responses={
            204: OpenApiResponse(description="Size deleted successfully."),
            400: OpenApiResponse(description="Cannot delete size due to validation (e.g., only size or has reserved stock)."),
            403: OpenApiResponse(description="User does not have permission to modify this product."),
            404: OpenApiResponse(description="Product or size not found."),
        },
    )
    def delete(self, request, product_id, size_id):
        product = get_object_or_404(Product, pk=product_id)

        # Check if the current user is the owner of the product
        if product.owner_id != request.user:
            logger.critical(
                "User %s attempted to delete size %s of product %s without permission.",
                request.user.id,
                size_id,
                product.id,
            )
            return Response(
                {"detail": "You do not have permission to modify this product."},
                status=status.HTTP_403_FORBIDDEN
            )

        size = get_object_or_404(Size, pk=size_id, product=product)

        # If product uses sizes, don't delete the last one
        total_sizes = product.sizes.count()
        if product.has_sizes and total_sizes == 1:
            return Response(
                {"detail": "Cannot delete the only size for this product."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent deletion if reserved_quantity > 0
        if size.reserved_quantity > 0:
            return Response(
                {"detail": "Cannot delete a size with reserved stock."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform a soft delete
        size.delete()

        return Response(
            {"message": f"Size '{size.size}' deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )


class DeleteProductOfferView(APIView):
    """
    Deletes the offer for a specific product by product_id.
    Only the product owner can perform this action.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={
            204: OpenApiResponse(description="Offer deleted successfully."),
            403: OpenApiResponse(description="User does not own this product."),
            404: OpenApiResponse(description="Product or offer not found."),
        },
        summary="Delete Product Offer",
        description="""
        Deletes the offer associated with a product.

        - Only the **product owner** can delete the offer.
        - Fails if no active offer exists.
        """,
    )
    def delete(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)

        # Check if the current user is the owner of the product
        if product.owner_id != request.user:
            logger.critical(
                "User %s attempted to delete offer on product %s without permission.",
                request.user.id,
                product.id,
            )
            return Response(
                {"detail": "You do not have permission to modify this product."},
                status=status.HTTP_403_FORBIDDEN
            )

        offer = get_object_or_404(Offer, product=product)
        offer.delete()

        return Response(
            {"message": f"Offer on product '{product.product_name}' deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
