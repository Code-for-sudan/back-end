from rest_framework import serializers
from models import EmailAttachment, EmailImage, EmailStyle, EmailTemplate

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


class EmailImageSerializer(serializers.ModelSerializer):
    """
    Serializer for the EmailImage model, handling serialization and deserialization of the 'image' field.
    Fields:
        image: The image file associated with the email.
    """
    class Meta:
        model = EmailImage
        fields = ['image']


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


class EmailTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for the EmailTemplate model, including nested serializers for attachments, images, and styles.
    Fields:
        - id: Integer, unique identifier of the email template.
        - name: String, name of the email template.
        - subject: String, subject line of the email template.
        - html_file: File, HTML content file for the email template.
        - plain_text_file: File, plain text content file for the email template.
        - attachments: List of attachments associated with the template (optional).
        - images: List of images associated with the template (optional).
        - styles: List of styles associated with the template (optional).
    Methods:
        - create(validated_data): Creates an EmailTemplate instance along with its related attachments, images, and styles from the provided validated data.
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
