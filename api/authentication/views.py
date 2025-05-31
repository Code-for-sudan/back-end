import logging
from rest_framework.decorators import api_view, permission_classes # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny
from rest_framework import status # type: ignore
from django.contrib.auth import authenticate

from accounts.models import User
from .utils import generate_jwt_tokens

logger = logging.getLogger('authentication_views') # Create Logger


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Handles user login by validating credentials and issuing JWT tokens.
    Args:
        request (Request): The HTTP request object containing user credentials.
    Returns:
        Response: 
            - 200 OK with access token in the response body and refresh token as an HTTP-only cookie if authentication is successful.
            - 400 BAD REQUEST with an error message if credentials are missing or invalid.
    Raises:
        KeyError: If 'email' or 'password' is not present in the request data.
    Side Effects:
        - Logs errors for missing credentials or invalid login attempts.
        - Sets the refresh token as an HTTP-only, secure cookie with SameSite=Lax.
    """

    try:
        email = request.data['email']
        password = request.data['password']
    except KeyError:
        logger.error('Email and password are required.')
        return Response(
            {
                'message': 'Email and password are required.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Authenticate the user
    user = authenticate(request, email=email, password=password)
    # If the user is not authenticated, return an error response
    if not user:
        logger.error('Invalid credentials.')
        response = Response(
            {
                'message': 'Invalid credentials.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        return response

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


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_confirm(request):
    """
    Handles password reset by verifying OTP and setting a new password.
    Args:
        request (Request): The HTTP request object containing email, OTP, and new password.
    Returns:
        Response:
            - 200 OK with a success message if OTP is valid and password is reset.
            - 400 BAD REQUEST with an error message if any field is missing, the user does not exist, or OTP is invalid.
    Raises:
        KeyError: If 'email', 'otp', or 'new_password' is not present in the request data.
    Side Effects:
        - Logs errors for missing fields, invalid OTP, or non-existent users.
        - Updates the user's password if OTP verification is successful.
    """
    try:
        email = request.data.get('email')
        otp = request.data.get('otp')
        new_password = request.data.get('new_password')
    except KeyError:
        logger.error('Email, OTP, and new password are required.')
        return Response({'message': 'Email, OTP, and new password are required.'}, status=status.HTTP_400_BAD_REQUEST)

    logger.info(f"Password reset attempt for email: {email}")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        logger.error(f"User with email {email} does not exist.")
        return Response({'message': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

    if not user.verify_otp(otp):
        logger.error(f"Invalid or expired OTP for user {email}.")
        return Response({'message': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()
    logger.info(f"Password reset successful for user {email}.")
    return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)