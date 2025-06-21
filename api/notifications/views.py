import logging
from rest_framework.views import APIView
from rest_framework.response import Response # type: ignore
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from drf_spectacular.utils import extend_schema


# Create a logger for this module
logger = logging.getLogger('notifications_views')


