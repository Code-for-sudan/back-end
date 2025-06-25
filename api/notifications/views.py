import logging
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAdminUser # type: ignore
from drf_spectacular.utils import extend_schema
from .models import EmailTemplate
from .serializers import EmailTemplateSerializer

# Create a logger for this module
logger = logging.getLogger('notifications_views')

@extend_schema(
    summary="Manage email templates",
    description="Create, retrieve, update, and delete email templates. Only admin users can access these endpoints.",
    tags=["Email Templates"]
)
class EmailTemplateViewSet(ModelViewSet):
    """
    A viewset for managing EmailTemplate objects.
    This viewset provides CRUD operations for email templates, allowing only admin users to access its endpoints.
    It supports multipart and form-data requests, enabling file uploads.
    Attributes:
        queryset (QuerySet): The set of EmailTemplate objects to operate on.
        serializer_class (Serializer): The serializer class used for validating and deserializing input, and for serializing output.
        parser_classes (tuple): Parsers to handle multipart and form-data requests.
        permission_classes (list): Permissions required to access this viewset (admin users only).
    """
    queryset = EmailTemplate.objects.all().order_by('id')
    serializer_class = EmailTemplateSerializer
    parser_classes = (MultiPartParser, FormParser)  # Accept form-data (file uploads)
    permission_classes = [IsAdminUser]  # Only allow admin users to access this view



# class 