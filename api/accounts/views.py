import logging
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework import status # type: ignore
from .models import User

# Crete the view logger
logger = logging.getLogger('accounts_views')

@api_view(['POST'])
@permission_classes([AllowAny])
def verfy_otp(request):
    user_email = request.data.get('email')
    otp_code = request.data.get('otp_code')

    if not user_email or not otp_code:
        logger.error('Email and OTP code are required.')
        return Response(
            {
                'message': 'Email and OTP code are required.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    user = User.objects.filter(email=user_email).first()

    # Verify the OTP code
    if not user.verify_otp(otp_code):
        return Response(
            {
                'message': 'Invalid OTP code.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Generate JWT tokens for the authenticated user
    access_token, refresh_token = generate_jwt_tokens(user)
    response = Response(
        {
            'message': 'Login successful.',
            'access_token': access_token,
        },
        status=status.HTTP_200_OK
    )

    # Set refresh token as an HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=str(refresh_token),
        httponly=True,  # Security feature
        secure=True,  # Use only in HTTPS
        samesite="Lax",  # Protect against CSRF
    )

    return response
