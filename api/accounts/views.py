import logging
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework import status # type: ignore
from .models import User
from .utils import generate_jwt_tokens

# Crete the view logger
logger = logging.getLogger('accounts_views')


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_otp(request):
    """
    Verify OTP for user email and return JWT tokens on success.
    """
    user_email = request.data.get('email', '').strip().lower()
    otp_code = request.data.get('otp_code')

    if not user_email or not otp_code:
        logger.error(f"Missing email or OTP in request: {request.data}")
        return Response(
            {'message': 'Email and OTP code are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.filter(email=user_email).first()
    if not user:
        logger.warning(f"User with email {user_email} not found.")
        return Response(
            {'message': 'User not found.'},
            status=status.HTTP_404_NOT_FOUND
        )

    if not user.verify_otp(otp_code):
        logger.warning(f"Invalid OTP for user {user_email}")
        return Response(
            {'message': 'Invalid OTP code.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    access_token, refresh_token = generate_jwt_tokens(user)
    response = Response(
        {
            'message': 'Login successful.',
            'access_token': access_token,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'first name': user.first_name,
            }
        },
        status=status.HTTP_200_OK
    )

    response.set_cookie(
        key="refresh_token",
        value=str(refresh_token),
        httponly=True,
        secure=True,
        samesite="Lax",
        max_age=1 * 24 * 60 * 60,  # 7 days
        path='/api/auth/'
    )

    return response
