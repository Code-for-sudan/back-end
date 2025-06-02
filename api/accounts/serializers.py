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


class BusinessOwnerSignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_null=True)
    whatsapp_number = serializers.CharField(required=False, allow_null=True)
    otp = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, min_length=6)
    gender = serializers.CharField()
    store_name = serializers.CharField()

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
        user = User.objects.create_user(**validated_data)
        business_owner = BusinessOwner.objects.create(user=user, store=store)
        return business_owner
