import os, logging
from rest_framework import serializers
from .models import EmailAttachment, EmailImage, EmailStyle, EmailTemplate

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
        fields = ['file']
        extra_kwargs = {'file': {'required': True}}

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
        fields = ['image']
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
        fields = ['style_file']
        extra_kwargs = {'style_file': {'required': True}}

    def validate_file(self, file):
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
    Serializer for the EmailTemplate model, handling nested relationships for attachments, images, and styles.

    Fields:
        - id: Integer, unique identifier of the email template.
        - name: String, name of the email template.
        - subject: String, subject line for the email template.
        - html_file: File, HTML content of the email template.
        - plain_text_file: File, plain text content of the email template.
        - attachments: List of EmailAttachmentSerializer objects, optional.
        - images: List of EmailImageSerializer objects, optional.
        - styles: List of EmailStyleSerializer objects, optional.

    Methods:
        - create(validated_data): Creates an EmailTemplate instance along with its related attachments, images, and styles.
        - update(instance, validated_data): Updates an EmailTemplate instance and its related attachments, images, and styles. Existing related objects are deleted and recreated if new data is provided.

    Notes:
        - Nested data for attachments, images, and styles are handled explicitly in create and update methods to ensure proper creation and association with the EmailTemplate instance.
    """
    attachments = EmailAttachmentSerializer(many=True, required=False)
    images = EmailImageSerializer(many=True, required=False)
    styles = EmailStyleSerializer(many=True, required=False)

    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'subject', 'html_file',
            'plain_text_file','attachments',
            'images', 'styles'
        ]
        read_only_fields = ['id']

    extra_kwargs = {
        'name': {'required': True},
        'subject': {'required': True},
        'html_file': {'required': True},
        'plain_text_file': {'required': True}
    }

    def create(self, validated_data):
        # Delete nested data from validated_data for the EmailTemplate creation
        # This is necessary to avoid conflicts with the EmailTemplate model fields.
        attachments_data = validated_data.pop('attachments', [])
        images_data = validated_data.pop('images', [])
        styles_data = validated_data.pop('styles', [])

        template = EmailTemplate.objects.create(**validated_data)

        for attachment in attachments_data:
            EmailAttachment.objects.create(template=template, **attachment)
        for image in images_data:
            EmailImage.objects.create(template=template, **image)
        for style in styles_data:
            EmailStyle.objects.create(template=template, **style)

        return template

    def update(self, instance, validated_data):
        attachments_data = validated_data.pop('attachments', None)
        images_data = validated_data.pop('images', None)
        styles_data = validated_data.pop('styles', None)

        # Update simple fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Optionally: clear and recreate related objects
        if attachments_data is not None:
            instance.attachments.all().delete()
            for attachment in attachments_data:
                EmailAttachment.objects.create(template=instance, **attachment)
        if images_data is not None:
            instance.images.all().delete()
            for image in images_data:
                EmailImage.objects.create(template=instance, **image)
        if styles_data is not None:
            instance.styles.all().delete()
            for style in styles_data:
                EmailStyle.objects.create(template=instance, **style)

        return instance
