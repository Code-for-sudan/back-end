import logging, os, re, random, string
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


def set_account_type_for_user(user, account_type):
    """
    Maps account_type string to is_store_owner boolean.
    """
    if account_type == "seller":
        user.is_store_owner = True
    else:
        user.is_store_owner = False
    user.save()


def generate_verification_code(length=6):
    """
    Generate a random verification code of specified length.
    Args:
        length (int): Length of the verification code (default 6)
    Returns:
        str: Generated verification code
    """
    return ''.join(random.choices(string.digits, k=length))


def validate_phone_number(phone_number):
    """
    Validate phone number format.
    Args:
        phone_number (str): Phone number to validate
    Returns:
        bool: True if valid, False otherwise
    """
    if not phone_number:
        return False
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone_number)
    
    # Check if it's a valid length (typically 10-15 digits for international numbers)
    if len(digits_only) < 10 or len(digits_only) > 15:
        return False
    
    # Basic pattern check for international format
    phone_pattern = r'^(\+?[1-9]\d{1,14})$'
    return bool(re.match(phone_pattern, digits_only))