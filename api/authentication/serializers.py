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


class GoogleAuthCodeSerializer(serializers.Serializer):
    """
    Serializer for handling Google OAuth2 authorization codes.
    Fields:
        code (CharField): The authorization code returned by Google after a successful login.
    """

    code = serializers.CharField(help_text="Authorization code returned by Google after login")



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
        validators=[serializers.RegexValidator(
            regex=r'^\d{6}$',
            message="OTP must be a 6-digit number.",
            code='invalid_otp'
        )],
        help_text="One-Time Password code"
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        max_length=128,
        help_text="New password for the user"
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
