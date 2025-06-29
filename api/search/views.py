import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from products.models import Product
from .documents import ProductDocument
from .serializers import ProductSearchSerializer
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

logger = logging.getLogger('search_views')

@extend_schema(
    parameters=[
        OpenApiParameter(name='q', description='Search query string', required=False, type=str),
        OpenApiParameter(name='p', description='Page number (default: 1)', required=False, type=int),
    ],
    responses={
        200: OpenApiResponse(
            response=ProductSearchSerializer(many=True),
            description='List of products matching the search query (paginated, 12 per page).'
        ),
        400: OpenApiResponse(
            description='Invalid page number or bad request.'
        ),
        500: OpenApiResponse(
            description='Internal server error during search.'
        ),
    },
    description="Search for products using Elasticsearch. Supports fuzzy search on product name, description, and category. Returns paginated results (12 per page).",
    summary="Product Search"
)
class ProductSearchView(APIView):
    """
    Search for products using Elasticsearch with fuzzy matching.
    Accepts 'q' as the search query and 'p' as the page number (default 1).
    Returns up to 12 products per page, paginated.
    If the search query is empty, returns a message indicating that.
    Args:
        request (Request): The HTTP request object containing 'q' and 'p' as query parameters.
    Returns:
        200 OK: JSON with 'results', 'page', and 'total'.
        400 BAD REQUEST: Invalid page number.
        500 INTERNAL SERVER ERROR: Error during search.
    """
    PAGE_SIZE = 12

    def get(self, request):
        try:
            query = request.GET.get('q', '')
            page = int(request.GET.get('p', 1))
            if not query.strip():
                logger.info("Search query is empty.")
                return Response(
                    {"message": "Search query is empty"},
                    status=status.HTTP_200_OK
                )
            if page < 1:
                logger.error(f"Invalid page number: {page}")
                return Response({"message": "Page number must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)
            start = (page - 1) * self.PAGE_SIZE
            end = start + self.PAGE_SIZE

            # Elasticsearch search
            search = ProductDocument.search().query(
                "multi_match",
                query=query,
                fields=['product_name', 'product_description', 'category'],
                fuzziness='AUTO',
            )
            results = search[start:end].execute()
            total = results.hits.total.value if hasattr(results.hits.total, 'value') else results.hits.total

            product_ids = [hit.meta.id for hit in results]
            products = Product.objects.filter(id__in=product_ids)
            serializer = ProductSearchSerializer(products, many=True)

            logger.info(f"Search successful: query='{query}', page={page}, results={len(products)}")
            return Response({
                "results": serializer.data,
                "page": page,
                "total": total
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Search error: {str(e)}", exc_info=True)
            return Response(
                {"message": "An error occurred while searching for products."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
