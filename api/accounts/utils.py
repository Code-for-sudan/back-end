import logging, os
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from django.conf import settings


# Create the logger for celery tasks
logger = logging.getLogger('accounts_utils')

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


def generate_activation_link(user):
    """
    Generate an activation link for a user or business owner.
    Args:
        user (User): The user instance.
    Returns:
        str: The activation link containing the token.
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(user).access_token)
    # You can use a dedicated activation token if you want, but JWT works fine for this purpose.
    base_url = getattr(
        settings,
        "FRONTEND_ACTIVATION_URL",
        "https://sudamall.ddns.net/account-activate"
    )
    return f"{base_url}?token={token}"
