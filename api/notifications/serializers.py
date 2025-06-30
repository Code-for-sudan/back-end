import os, logging
from rest_framework import serializers
from .models import EmailAttachment, EmailImage, EmailStyle, EmailTemplate
from accounts.models import Cart

# Create the logger instance for the serializers
logger = logging.getLogger('notifications_serializers')


class EmailAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for the EmailAttachment model.
    This serializer handles the serialization and deserialization of EmailAttachment instances,
    specifically exposing the 'file' field for use in API requests and responses.
    Fields:
        file (FileField): The file attached to the email.
    """
    class Meta:
        model = EmailAttachment
        fields = ['id', 'template', 'file']
        extra_kwargs = {'file': {'required': True,}}

    def validate_file(self, file):
        if file is None:
            return file
        allowed_file_extensions = ['jpg', 'jpeg', 'png', 'pdf', 'docx', 'xlsx']
        allowed_file_size = 10 * 1024 * 1024  # 10MB

        file_extension = os.path.splitext(file.name)[1][1:].lower()
        if file_extension not in allowed_file_extensions:
            logger.error('Unsupported file extension. Allowed: jpg, jpeg, png, pdf, docx, xlsx.')
            raise serializers.ValidationError(
                'Unsupported file extension. Allowed: jpg, jpeg, png, pdf, docx, xlsx.'
            )

        if file.size > allowed_file_size:
            logger.error('The file is too large. Max size: 5MB.')
            raise serializers.ValidationError(
                'The file is too large. Max size: 10MB.'
            )
        return file


class EmailImageSerializer(serializers.ModelSerializer):
    """
    Serializer for the EmailImage model, handling serialization and deserialization of the 'image' field.
    Fields:
        image: The image file associated with the email.
    """
    class Meta:
        model = EmailImage
        fields = ['id', 'template', 'image']
        extra_kwargs = {'image': {'required': True}}

    def validate_image(self, image):
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


class EmailStyleSerializer(serializers.ModelSerializer):
    """
    Serializer for the EmailStyle model, handling the serialization and deserialization
    of the 'style_file' field. This serializer is typically used to validate and
    transform EmailStyle instances to and from JSON representations for API endpoints.
    Fields:
        style_file: The file field representing the email style file.
    """
    class Meta:
        model = EmailStyle
        fields = ['id', 'template', 'style_file']
        extra_kwargs = {'style_file': {'required': True}}

    def validate_style_file(self, file):
        if file is None:
            return file
        allowed_file_extensions = ['css']
        allowed_file_size = 1 * 1024 * 1024  # 1MB

        file_extension = os.path.splitext(file.name)[1][1:].lower()
        if file_extension not in allowed_file_extensions:
            logger.error('Unsupported file extension. Allowed: css.')
            raise serializers.ValidationError(
                'Unsupported file extension. Allowed: .css.'
            )

        if file.size > allowed_file_size:
            logger.error('The file is too large. Max size: 5MB.')
            raise serializers.ValidationError(
                'The file is too large. Max size: 1MB.'
            )
        return file


class EmailTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for the EmailTemplate model.
    This serializer handles the serialization and deserialization of EmailTemplate instances,
    enforcing that the following fields are required:
        - name: The name of the email template.
        - subject: The subject line for the email.
        - html_file: The HTML content file for the email template.
        - plain_text_file: The plain text content file for the email template.
    Fields:
        - id (int): Unique identifier for the email template.
        - name (str): Name of the template (required).
        - subject (str): Subject of the email (required).
        - html_file (File): HTML file for the email content (required).
        - plain_text_file (File): Plain text file for the email content (required).
    """
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'subject', 'html_file',
            'plain_text_file'
        ]
    extra_kwargs = {
        'name': {'required': True},
        'subject': {'required': True},
        'html_file': {'required': True},
        'plain_text_file': {'required': True}
    }


class AdminSendEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        help_text="The email address to send the email to."
    )
    template_id = serializers.PrimaryKeyRelatedField(
        queryset=EmailTemplate.objects.all(),
        required=True,
        help_text="The email template to use for sending the email."
    )

###TODO:
# location (country, city)

# last_purchase_date (last 30, 60, 90 days)

# user_type (new vs returning)

# cart_status (active cart, abandoned cart)

# total_spent (tiered spenders: low, mid, high)
class CartSerializer(serializers.ModelSerializer):
    """
    Serializer for the Cart model.
    This serializer automatically includes all fields from the Cart model.
    It is used to convert Cart model instances to and from JSON representations,
    facilitating the creation, retrieval, update, and deletion of cart data via API endpoints.
    Attributes:
        Meta (class): Configuration for the serializer, specifying the model and fields to include.
    """
    class Meta:
        model = Cart
        fields = '__all__'


class GroupTargetingSerializer(serializers.Serializer):
    """
    Serializer for targeting user groups based on specified filters and grouping fields.
    Attributes:
        filters (DictField): Optional dictionary of filters to apply when grouping users.
        group_by (ListField): Optional list of fields to group the results by.
        VALID_FIELDS (list): List of valid fields that can be used for filtering and grouping.
    Validation:
        - Ensures that all fields specified in 'group_by' and keys in 'filters' are within VALID_FIELDS.
        - Raises a ValidationError if any invalid field is provided.
    Intended Use:
        Use this serializer to validate and process input data for APIs that support dynamic user segmentation
        based on account status, cart status, account creation date, last purchase date, location, and total spent.
    """

    filters = serializers.DictField(
        required=False,
        help_text="Filters to apply when grouping users."
    )
    group_by = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Fields to group the results by."
    )

    template_id = serializers.PrimaryKeyRelatedField(
        queryset=EmailTemplate.objects.all(),
        required=True,
        help_text="The email template to use for sending the email."
    )

    VALID_FIELDS = [
        'is_active', 'cart_status', 'account_date',
        'last_purchase_date', 'location', 'total_spent'
    ]

    def validate(self, data):
        group_by = data.get('group_by', [])
        for field in group_by:
            if field not in self.VALID_FIELDS:
                logger.error(f"Invalid field '{field}' in group_by. Valid fields are: {', '.join(self.VALID_FIELDS)}.")
                raise serializers.ValidationError(
                    f"Invalid field '{field}' in group_by. Valid fields are: {', '.join(self.VALID_FIELDS)}."
                )
        filters = data.get('filters', {})
        for key in filters:
            if key not in self.VALID_FIELDS:
                logger.error(f"Invalid filter '{key}'. Valid fields are: {', '.join(self.VALID_FIELDS)}.")
                raise serializers.ValidationError(
                    f"Invalid filter '{key}'. Valid fields are: {', '.join(self.VALID_FIELDS)}."
                )

        return data


class NewsletterSubscriptionSerializer(serializers.Serializer):
    """
    Serializer for handling newsletter subscription requests.
    Fields:
        subscribe (bool): Indicates whether the user wants to subscribe (True) or unsubscribe (False) from the newsletter.
    """
    subscribe = serializers.BooleanField(help_text="Set to true to subscribe, false to unsubscribe.")
