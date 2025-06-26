import logging
from rest_framework.response import Response, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAdminUser # type: ignore
from drf_spectacular.utils import extend_schema
from .models import EmailTemplate
from .serializers import EmailTemplateSerializer

# Create a logger for this module
logger = logging.getLogger('notifications_views')

@extend_schema(
    summary="Product CRUD",
    description="Product CRUD operations. Supports listing, creating, retrieving, updating, and deleting products."
)
class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing email templates in the notification system.
    This viewset provides CRUD operations for the EmailTemplate model, allowing only admin users to access these endpoints.
    It supports file uploads via multipart/form-data and logs all create, update, retrieve, and delete actions.
    Actions:
        - create: Create a new email template. Returns a success message and the created data on success, or error details on failure.
        - update: Update an existing email template (partial updates allowed). Returns a success message and updated data on success, or error details on failure.
        - retrieve: Retrieve a specific email template by ID. Returns a success message and the template data.
        - destroy: Delete a specific email template by ID. Returns a success message upon successful deletion.
    Permissions:
        - Only accessible by admin users.
    Parsers:
        - Supports MultiPartParser and FormParser for handling file uploads.
    Logging:
        - Logs all create, update, retrieve, and delete actions with relevant details.
    """

    serializer_class = EmailTemplateSerializer
    queryset = EmailTemplate.objects.all().order_by('id')
    parser_classes = (MultiPartParser, FormParser)  # Accept form-data (file uploads)
    permission_classes = [IsAdminUser]  # Only allow admin users to access this
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email template created successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email template created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        logger.error(f"Email template creation failed: {serializer.errors}")
        return Response(
            {
                "message": "Email template creation failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email template updated successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email template updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        logger.error(f"Email template update failed: {serializer.errors}")
        return Response(
            {
                "message": "Email template update failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Email template retrieved successfully: {serializer.data}")
        return Response(
            {
                "message": "Email template retrieved successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        logger.info(f"Email template deleted successfully: {instance.id}")
        return Response(
            {
                "message": "Email template deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )
