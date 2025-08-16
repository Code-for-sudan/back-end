import logging, re
from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import BusinessOwner
from stores.models import Store


# Get the user model
User = get_user_model()
# Create a logger for this module
logger = logging.getLogger('authentication_serializers')


class LoginSerializer(serializers.Serializer):
    """
    Serializer for handling user login authentication.

    Validates the provided email and password:
    - Checks if a user with the given email exists.
    - Ensures the user's account is active.
    - Authenticates the user using the provided credentials.

    Raises:
        serializers.ValidationError: If the email does not exist, the account is inactive,
        or the authentication fails. If the account is inactive, a custom attribute
        'resend_verification_link' is set to True on the exception.

    Returns:
        dict: The validated data with the authenticated user instance added under the 'user' key.
    """
    email = serializers.EmailField(
        required=True,
        max_length=254,
        help_text="User's email address"
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        min_length=8,
        max_length=128,
        help_text="User's password"
    )

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        # Try to get the user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.error(f"[LoginSerializer] No user found for email: {email}")
            raise serializers.ValidationError("Invalid email or password.")

        # Check if the account is active
        if not user.is_active:
            logger.warning(f"[LoginSerializer] Inactive user attempted login: {email}")
            error = serializers.ValidationError(
                "Email already registered but not verified."
            )
            error.resend_verification_link = True  # Custom attribute
            raise error

        # Now authenticate (will check password)
        user = authenticate(username=email, password=password)
        if not user:
            logger.error(f"[LoginSerializer] Authentication failed for email: {email}")
            raise serializers.ValidationError("Invalid email or password.")

        data['user'] = user
        return data


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
    """
    Serializer for setting the account type of a user.
    Fields:
        account_type (ChoiceField): Specifies the type of account. 
            Choices are 'seller' or 'buyer'.
    Usage:
        Use this serializer to validate and process requests where a user selects 
        their account type during registration or profile update.
    """
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
    Serializer for setting up or updating a seller's store information.

    Fields:
        store_name (CharField): Name of the store or business.
        store_location (CharField): Physical location of the store (if applicable).
        store_type (CharField): Type of store (e.g., 'retail', 'online', etc.).
        store_description (CharField): Brief description of the store or business.

    Methods:
        update(instance, validated_data):
            Updates the given Store instance with validated data.

        create(validated_data):
            Creates or updates the store associated with the business owner profile of the current user.
            Raises ValidationError if the business owner profile is not found.
    """
    store_name = serializers.CharField(
        max_length=255,
        help_text="Name of your store or business."
    )
    store_location = serializers.CharField(
        max_length=255,
        help_text="Physical location of your store (if applicable)."
    )
    store_type = serializers.CharField(
        max_length=100,
        help_text="Type of store (e.g., 'retail', 'online', etc.)."
    )
    store_description = serializers.CharField(
        max_length=500,
        help_text="Brief description of your store or business."
    )

    def update(self, instance, validated_data):
        # instance is the Store object
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def create(self, validated_data):
        user = self.context.get('user')
        # Get the business owner profile
        try:
            business_owner = user.business_owner_profile
        except BusinessOwner.DoesNotExist:
            logger.error(f"No business owner profile found for user: {user.email}")
            raise serializers.ValidationError(
                "Business owner profile not found for this user."
            )

        store = business_owner.store
        # Update store fields
        # Map serializer fields to Store model fields
        store.name = validated_data.get("store_name", store.name)
        store.location = validated_data.get("store_location", store.location)
        store.store_type = validated_data.get("store_type", store.store_type)
        store.description = validated_data.get("store_description", store.description)
        store.save()
        return store



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
    """
    Serializer for verifying a password reset request using email and OTP.
    Fields:
        email (EmailField): The user's email address. Required, max length 254.
        otp (CharField): The one-time password code. Required, exactly 6 characters, write-only.
    Used to validate the data required for verifying a password reset request.
    """
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
    random_token = serializers.CharField(
        required=True,
        max_length=64,
        min_length=40,
        write_only=True,
        help_text="Short-lived token for password update"
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="New password for the user"
    )

    def validate_password(self, attrs):
        """
        Validates the strength of a password.
        The password must meet the following criteria:
            - At least 8 characters long
            - Contains at least one digit
            - Contains at least one uppercase letter
            - Contains at least one lowercase letter
            - Contains at least one special character (!@#$%^&*(),.?":{}|<>)
        Args:
            attrs (str): The password string to validate.
        Raises:
            serializers.ValidationError: If the password does not meet any of the criteria.
        Returns:
            str: The validated password string.
        """
        password = attrs
        if len(password) < 8:
            logger.error("Password must be at least 8 characters long.")
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'\d', password):
            logger.error("Password must contain at least one digit.")
            raise serializers.ValidationError("Password must contain at least one digit.")
        if not re.search(r'[A-Z]', password):
            logger.error("Password must contain at least one uppercase letter.")
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            logger.error("Password must contain at least one lowercase letter.")
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            logger.error("Password must contain at least one special character.")
            raise serializers.ValidationError("Password must contain at least one special character.")
        return password

class ResendVerificationSerializer(serializers.Serializer):
    """
    Serializer for handling requests to resend email verification.
    Fields:
        email (EmailField): The user's email address to which the verification email will be resent.
    """
    email = serializers.EmailField(
        required=True,
        max_length=254,
        help_text="User's email address"
    )
