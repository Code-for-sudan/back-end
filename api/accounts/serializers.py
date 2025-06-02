import os, logging
from rest_framework import serializers # type: ignore
from .models import User, BusinessOwner
from stores.models import Store

# Create the looger instance for the celery tasks
logger = logging.getLogger('user_serializer')


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    Handles serialization and deserialization of user data, including validation for profile pictures and secure password handling.
    Fields:
        - email (str): Required. The user's email address.
        - first_name (str): Required. The user's first name.
        - last_name (str): Required. The user's last name.
        - profile_picture (Image): Optional. The user's profile image. Must be jpg, jpeg, or png and not exceed 5MB.
        - phone_number (str): Optional. The user's phone number.
        - whatsapp_number (str): Optional. The user's WhatsApp number.
        - otp (str): Optional. One-time password for verification.
        - password (str): Required. Write-only. The user's password (minimum 6 characters).
        - gender (str): Required. The user's gender.
    Methods:
        - validate_profile_picture(image): Validates the uploaded profile picture for allowed file types and size.
        - create(validated_data): Creates a new user instance using the validated data.
    """

    # Set the password field as write-only to prevent it from being serialized
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'profile_picture',
            'phone_number',
            'whatsapp_number',
            'otp',
            'password',
            'gender'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'password': {'required': True},
            'gender': {'required': True}
        }

    def validate_profile_picture(self, image):
        if image is None:
            return image
        allowed_image_extensions = ['jpg', 'jpeg', 'png']
        allowed_image_size = 5 * 1024 * 1024  # 5MB

        image_extension = os.path.splitext(image.name)[1][1:].lower()
        if image_extension not in allowed_image_extensions:
            logger.error('Unsupported file extension. Allowed: jpg, jpeg, png.')
            raise serializers.ValidationError(
                'Unsupported file extension. Allowed: jpg, jpeg, png.'
            )

        if image.size > allowed_image_size:
            logger.error('The image is too large. Max size: 5MB.')
            raise serializers.ValidationError(
                'The image is too large. Max size: 5MB.'
            )
        return image

    def create(self, validated_data):
        # Create a new user with the validated data
        return User.objects.create_user(**validated_data)


class BusinessOwnerSignupSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new BusinessOwner along with their associated Store.
    Fields:
        - email: Email address of the business owner.
        - first_name: First name of the business owner.
        - last_name: Last name of the business owner.
        - profile_picture: Optional profile image, validated for file type and size.
        - phone_number: Contact phone number.
        - whatsapp_number: WhatsApp contact number.
        - otp: One-time password for verification (write-only).
        - password: Account password (write-only, minimum 6 characters).
        - gender: Gender of the business owner.
        - store_name: Name of the store to be created (required).
    Validation:
        - Ensures profile_picture is a jpg, jpeg, or png file and does not exceed 5MB.
    Creation:
        - Creates a Store instance with the provided store_name.
        - Creates a BusinessOwner user associated with the new Store.
    Raises:
        - serializers.ValidationError: If profile_picture is invalid.
    """

    store_name = serializers.CharField(required=True)

    class Meta:
        model = BusinessOwner
        fields = [
            'email',
            'first_name',
            'last_name',
            'profile_picture',
            'phone_number',
            'whatsapp_number',
            'otp',
            'password',
            'gender',
            'store_name'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 6},
            'otp': {'write_only': True},
        }

    def validate_profile_picture(self, image):
        if image is None:
            return image
        allowed_image_extensions = ['jpg', 'jpeg', 'png']
        allowed_image_size = 5 * 1024 * 1024  # 5MB

        image_extension = os.path.splitext(image.name)[1][1:].lower()
        if image_extension not in allowed_image_extensions:
            logger.error('Unsupported file extension. Allowed: jpg, jpeg, png.')
            raise serializers.ValidationError(
                'Unsupported file extension. Allowed: jpg, jpeg, png.'
            )

        if image.size > allowed_image_size:
            logger.error('The image is too large. Max size: 5MB.')
            raise serializers.ValidationError(
                'The image is too large. Max size: 5MB.'
            )
        return image

    def create(self, validated_data):
        store_name = validated_data.pop('store_name')
        store = Store.objects.create(name=store_name)

        # Create the BusinessOwner instance
        business_owner = BusinessOwner.objects.create_user(
            store=store,
            **validated_data
        )
        return business_owner
