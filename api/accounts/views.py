
import logging
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore

@api_view(['POST'])
@permission_classes([AllowAny])
def sign_up(request):
    pass