import logging
import re
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth import get_user_model

# Get the user model
User = get_user_model()
# Create a logger for this module
logger = logging.getLogger('authentication_serializers')


class LoginSerializer(serializers.Serializer):
    """
    A Login serializer for user authentication validating user's email and password, returning the user instance if valid.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(username=email, password=password)
        if not user:
            # Log the failed authentication attempt
            logger.error(f"[LoginSerializer] Authentication failed for email: {email}")
            raise serializers.ValidationError("Invalid email or password.")
        data['user'] = user
        return data


from rest_framework import serializers


class GoogleAuthCodeSerializer(serializers.Serializer):
    """
    Serializer for handling Google OAuth2 authorization code and optional state.
    
    Fields:
        code (CharField): The authorization code returned by Google after a successful login.
        state (CharField, optional): Optional state information passed during OAuth initiation (e.g., account type).
    """
    code = serializers.CharField(
        help_text="Authorization code returned by Google after login",
        required=True
    )
    state = serializers.CharField(
        help_text="Optional state string passed to Google (e.g., 'accountType=seller')",
        required=False,
        allow_blank=True
    )


class SetAccountTypeSerializer(serializers.Serializer):
    ACCOUNT_TYPE_CHOICES = [
        ('seller', 'Seller'),
        ('buyer', 'Buyer'),
    ]
    account_type = serializers.ChoiceField(
        choices=ACCOUNT_TYPE_CHOICES,
        help_text="Specify the type of account: 'seller' or 'buyer'."
    )


class SellerSetupSerializer(serializers.Serializer):
    """
    Serializer to gather additional setup data for sellers.
    
    Fields:
        store_name (str): Name of the seller's store.
        business_email (str): Business email address (can differ from user email).
    """
    store_name = serializers.CharField(
        max_length=255,
        help_text="Name of your store or business."
    )
    business_email = serializers.EmailField(
        help_text="Email used for business communication."
    )



class ResetPasswordRequestSerializer(serializers.Serializer):
    """
    Serializer for handling password reset requests via OTP.
    Fields:
        email (EmailField): The email address associated with the user account. Required, max length 254.
    """

    email = serializers.EmailField(
        required=True,
        max_length=254,
        help_text="The email address associated with the user account."
    )



class ResetPasswordrequestVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        max_length=254,
        help_text="User's email address"
    )
    otp = serializers.CharField(
        required=True,
        max_length=6,
        min_length=6,
        write_only=True,
        help_text="One-Time Password code"
    )
    

class RequestUpdatePasswordSerializer(serializers.Serializer):
    """
    Serializer for handling user password update requests.
    Fields:
        email (EmailField): The user's email address. Required, maximum length 254 characters.
        new_password (CharField): The new password for the user. Required, write-only, minimum length 8, maximum length 128 characters.
    """
    email = serializers.EmailField(
        required=True,
        max_length=254,
        help_text="User's email address"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        max_length=128,
        help_text="New password for the user"
    )
