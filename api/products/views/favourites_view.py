import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse

from products.models import Product
from products.serializers import ProductSerializer
logger = logging.getLogger('accounts_favourites')


@extend_schema(
    description="Get all favourite products of the current user.",
    summary="Get Favourites"
)
class FavouriteProductsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        favourites = request.user.favourite_products.all()
        serializer = ProductSerializer(favourites, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddToFavouritesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add Product to Favourites",
        description="Adds a product to the authenticated user's list of favourites.",
        responses={
            200: OpenApiResponse(description="Product added to favourites."),
            404: OpenApiResponse(description="Product not found."),
        },
    )
    def post(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."},
                            status=status.HTTP_404_NOT_FOUND)

        if request.user.favourite_products.filter(id=product.id).exists():
            # Already in favourites
            return Response({"message": "Product is already in favourites."},
                            status=status.HTTP_200_OK)

        request.user.favourite_products.add(product)
        return Response({"message": "Product added to favourites."},
                        status=status.HTTP_200_OK)


class RemoveFromFavouritesView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Remove a product from the current user's favourites.",
        summary="Remove from Favourites"
    )
    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found."},
                            status=status.HTTP_404_NOT_FOUND)

        if not request.user.favourite_products.filter(id=product.id).exists():
            # Not in favourites
            return Response({"message": "Product is not in favourites."},
                            status=status.HTTP_200_OK)

        request.user.favourite_products.remove(product)
        return Response({"message": "Product removed from favourites."},
                        status=status.HTTP_200_OK)
