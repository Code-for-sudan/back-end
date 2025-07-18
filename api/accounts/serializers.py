import os, logging
from rest_framework import serializers # type: ignore
from django.db import transaction
from phonenumber_field.serializerfields import PhoneNumberField
from .models import User, BusinessOwner
from stores.models import Store

# Create the looger instance for the celery tasks
logger = logging.getLogger('accounts_serializers')


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
    # Set phone_number and whatsapp_number as optional fields
    phone_number = PhoneNumberField(required=False, allow_null=True)
    whatsapp_number = PhoneNumberField(required=False, allow_null=True)
    account_type = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'profile_picture',
            'password',
            'gender',
            'phone_number',
            'whatsapp_number',
            'password',
            'account_type'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'password': {'required': True},
            'gender': {'required': True},
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

    def get_account_type(self, obj):
        return "seller" if obj.is_store_owner else "buyer"



class BusinessOwnerSignupSerializer(serializers.Serializer):
    """
    Serializer for business owner signup, handling both user and store creation.

    Fields:
        email (EmailField): User's email address.
        first_name (CharField): User's first name.
        last_name (CharField): User's last name.
        profile_picture (ImageField): Optional user profile picture (jpg, jpeg, png, max 5MB).
        phone_number (PhoneNumberField): Optional user phone number.
        whatsapp_number (PhoneNumberField): Optional user WhatsApp number.
        password (CharField): User's password (write-only, min length 6).
        gender (CharField): User's gender.
        store_name (CharField): Store name (required, write-only).
        store_location (CharField): Store location (required, write-only).
        description (CharField): Store description (required, write-only).
        store_type (CharField): Store type (required, write-only).
        accountType (CharField): Account type (read-only, "seller" or "buyer").

    Methods:
        validate_profile_picture(image): Validates profile picture format and size.
        create(validated_data): Creates User, Store, and BusinessOwner instances atomically.
        get_accountType(obj): Returns account type based on user's store ownership.
    """
    user_id = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', required=True)
    first_name = serializers.CharField(source='user.first_name', required=True)
    last_name = serializers.CharField(source='user.last_name', required=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', required=False, allow_null=True)
    phone_number = PhoneNumberField(required=False, allow_null=True)
    whatsapp_number = PhoneNumberField(required=False, allow_null=True)
    password = serializers.CharField(source='user.password', write_only=True, min_length=6)
    gender = serializers.CharField(source='user.gender')
    account_type = serializers.CharField(source='user.account_type', read_only=True)

    # Store fields (all required)
    store_name = serializers.CharField(write_only=True, required=True)
    store_location = serializers.CharField(write_only=True, required=True)
    description = serializers.CharField(write_only=True, required=True)
    store_type = serializers.CharField(write_only=True, required=True)

    def get_user_id(self, obj):
        return obj.user.id if obj.user else None

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
        store_location = validated_data.pop('store_location')
        description = validated_data.pop('description')
        store_type = validated_data.pop('store_type')
        user_data = validated_data.pop('user')
        user_data['account_type'] = 'seller'  # <-- Set account type to seller
        user_data['is_store_owner'] = True # <-- Set is_store_owner to True
        with transaction.atomic():
            store = Store.objects.create(
                name=store_name,
                location=store_location,
                description=description,
                store_type=store_type
            )
            user = User.objects.create_user(**user_data)
            business_owner = BusinessOwner.objects.create(user=user, store=store)
        return business_owner

    def get_account_type(self, obj):
        return "seller" if obj.user.is_store_owner else "buyer"
