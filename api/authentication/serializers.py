import logging
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