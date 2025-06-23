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


class ResetPasswordConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset via OTP.
    Fields:
        email: User's email address.
        otp: One-time password sent to the user.
        new_password: The new password to set (must meet complexity requirements).
    Methods:
        validate_new_password: Validates the new password using a regex rule.
    Side Effects:
        - Logs validation errors.
    """
    email = serializers.EmailField()
    otp = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        # Regex: at least one letter, one digit, only letters/digits, min 8 chars
        pattern = r'^(?=.*[a-zA-Z])(?=.*[0-9])[a-zA-Z0-9]{8,}$'
        if not re.match(pattern, value):
            logger.error("[ResetPasswordConfirmSerializer] Password validation failed: does not meet complexity requirements.")
            raise serializers.ValidationError(
                "Password must be at least 8 characters long, contain both letters and numbers, and have only letters and digits."
            )
        return value

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



class ResetPasswordConfirmRequestSerializer(serializers.Serializer):
    """
    Serializer for confirming a password reset request.
    Fields:
        email (EmailField): User's email address.
        otp (CharField): One-Time Password code sent to the user.
        new_password (CharField): New password to set for the user.
    """

    email = serializers.EmailField(help_text="User's email address")
    otp = serializers.CharField(help_text="One-Time Password code")
    new_password = serializers.CharField(help_text="New password for the user")

class ResetPasswordRequestSerializer(serializers.Serializer):
    """
    Serializer for handling password reset requests.
    Fields:
        email (EmailField): User's email address to send the password reset instructions.
    """

    email = serializers.EmailField(help_text="User's email address")