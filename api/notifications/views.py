import logging
from rest_framework.viewsets import ModelViewSet
from .models import EmailTemplate
from .serializers import EmailTemplateSerializer
from rest_framework.parsers import MultiPartParser, FormParser

# Create a logger for this module
logger = logging.getLogger('notifications_views')


class EmailTemplateViewSet(ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    parser_classes = (MultiPartParser, FormParser)  # Accept form-data (file uploads)
