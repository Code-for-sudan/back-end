import logging
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework import status # type: ignore
from django.shortcuts import render
from .models import User
from .utils import generate_jwt_tokens

# Crete the view logger
logger = logging.getLogger('accounts_views')


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def verify_otp(request):
    """
    Handles OTP verification for user login.
    This function verifies the OTP (One-Time Password) provided by the user
    and returns a response indicating the success or failure of the verification.
    If successful, it generates JWT tokens for the user and sets a refresh token
    as an HTTP-only cookie.
    Args:
        request (Request): The HTTP request object containing the user's email
                           and OTP code in the request data.
    Returns:
        Response: A Django REST framework Response object with the following:
            - HTTP 200 OK: If the OTP verification is successful, returns a success
              message, access token, and user details.
            - HTTP 400 Bad Request: If the email or OTP code is missing, or if the
              OTP code is invalid.
            - HTTP 404 Not Found: If no user is found with the provided email.
    Side Effects:
        - Sets a secure, HTTP-only cookie for the refresh token with a 1-day expiration.
    Raises:
        None
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
