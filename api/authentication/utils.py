import logging, os
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore


def generate_jwt_tokens(user):
    """
    Generate JWT access and refresh tokens for a given user.
    Args:
        user (User): The user instance for whom the tokens are being generated.
    Returns:
        tuple: A tuple containing the access token (str) and the refresh token (str).
    """
    
    refresh = RefreshToken.for_user(user)

    # You can customize the expiration time here if needed
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return access_token, refresh_token
