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
    """
    Serializer for handling business owner sign-up.
    Fields:
        email (EmailField): The email address of the user (required).
        first_name (CharField): The first name of the user (required).
        last_name (CharField): The last name of the user (required).
        profile_picture (ImageField): Optional profile picture for the user.
        phone_number (CharField): Optional phone number of the user.
        whatsapp_number (CharField): Optional WhatsApp number of the user.
        otp (CharField): One-time password for verification (write-only, optional).
        password (CharField): Password for the user account (write-only, required, min_length=6).
        gender (CharField): Gender of the user.
        store_name (CharField): Name of the store to be created (write-only, required).
    Methods:
        validate_profile_picture(image):
            Validates the uploaded profile picture for allowed extensions (jpg, jpeg, png)
            and maximum file size (5MB).
        create(validated_data):
            Creates a new Store, User, and BusinessOwner instance based on the validated data.
    Raises:
        serializers.ValidationError: If the profile picture does not meet extension or size requirements.
    """

    email = serializers.EmailField(source='user.email', required=True)
    first_name = serializers.CharField(source='user.first_name', required=True)
    last_name = serializers.CharField(source='user.last_name', required=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', required=False, allow_null=True)
    phone_number = serializers.CharField(source='user.phone_number', required=False, allow_null=True)
    whatsapp_number = serializers.CharField(source='user.whatsapp_number', required=False, allow_null=True)
    otp = serializers.CharField(source='user.otp', write_only=True, required=False)
    password = serializers.CharField(source='user.password', write_only=True, min_length=6)
    gender = serializers.CharField(source='user.gender')
    store_name = serializers.CharField(write_only=True, required=True)

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
        user_data = validated_data.pop('user')
        store = Store.objects.create(name=store_name)
        user = User.objects.create_user(**user_data)
        business_owner = BusinessOwner.objects.create(user=user, store=store)
        return business_owner
