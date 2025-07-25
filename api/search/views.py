import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework_simplejwt.authentication import JWTAuthentication
from accounts.models import BusinessOwner
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
            response=ProductSearchSerializer,
            description='Paginated list of products matching the search query (12 per page). '
                        'If the user is a business owner, results are limited to their store.'
        ),
        400: OpenApiResponse(
            description='Invalid page number or bad request.'
        ),
        500: OpenApiResponse(
            description='Internal server error during search.'
        ),
    },
    description="""
    Search for products using Elasticsearch. Supports fuzzy matching on product name, description, and category.
    
    - Anonymous and buyer users: Search all available products.
    - Authenticated business owners: Search is limited to their own store's products.
    
    JWT authentication (via header or cookie) is optional and used to determine access level.
    """,
    summary="Product Search with Role-Based Filtering"
)
class ProductSearchView(APIView):
    """
    Search for products using Elasticsearch with fuzzy matching.
    
    Behavior:
    - If the request is unauthenticated or the user is not a business owner, it searches all products.
    - If the user is authenticated and a business owner, it restricts the search to products in their store only.
    
    Authentication is optional (JWT token via Authorization header or cookie).
    
    Accepts:
        - 'q': Search query string
        - 'p': Page number (default is 1)
    
    Returns:
        - 200 OK: JSON with paginated search results (12 per page), current page, and total count.
        - 400 BAD REQUEST: If the page number is invalid or query is missing.
        - 500 INTERNAL SERVER ERROR: If an error occurs during search.
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    PAGE_SIZE = 12

    def get(self, request):
        try:
            query = request.GET.get('q', '')
            page = int(request.GET.get('p', 1))

            if not query.strip():
                logger.info("Search query is empty.")
                return Response({"message": "Search query is empty"}, status=status.HTTP_200_OK)

            if page < 1:
                return Response({"message": "Page number must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

            start = (page - 1) * self.PAGE_SIZE
            end = start + self.PAGE_SIZE

            # Start the search query
            base_query = ProductDocument.search().query(
                "multi_match",
                query=query,
                fields=['product_name', 'product_description', 'category'],
                fuzziness='AUTO',
            )

            # Check if the authenticated user is a business owner
            user = request.user
            if user.is_authenticated:
                try:
                    business_owner = BusinessOwner.objects.get(user=user)
                    store_id = business_owner.store.id
                    base_query = base_query.filter("term", store_id=store_id)
                    logger.info(f"Filtering by store_id={store_id} for business owner user_id={user.id}")
                except BusinessOwner.DoesNotExist:
                    logger.info(f"User {user.id} is not a business owner.")
            else:
                logger.info("Unauthenticated user search.")

            results = base_query[start:end].execute()
            total = results.hits.total.value if hasattr(results.hits.total, 'value') else results.hits.total

            product_ids = [hit.meta.id for hit in results]
            products = Product.objects.filter(id__in=product_ids)
            serializer = ProductSearchSerializer(products, many=True)

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
