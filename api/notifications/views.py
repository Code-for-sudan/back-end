import logging
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated# type: ignore
from rest_framework.throttling import  AnonRateThrottle, ScopedRateThrottle
from drf_spectacular.utils import extend_schema
from .models import EmailTemplate, EmailAttachment, EmailImage, EmailStyle
from accounts.models import User
from notifications.tasks import send_email_task, delete_email_task, send_newsletter_task
from .serializers import (
    EmailTemplateSerializer,
    EmailAttachmentSerializer,
    EmailImageSerializer,
    EmailStyleSerializer,
    AdminSendEmailSerializer,
    GroupTargetingSerializer,
    NewsletterSubscriptionSerializer,
    ScheduleNewsletterSerializer
)
from django.db.models import Count

# Create a logger for this module
logger = logging.getLogger('notifications_views')

class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing email templates, supporting creation, retrieval, updating, and deletion.
    This viewset provides the following endpoints for admin users:
    - Create a new email template with support for HTML, plain text files, attachments, images, and styles.
    - Update an existing email template, allowing partial updates.
    - Retrieve a specific email template by its ID.
    - Delete a specific email template by its ID.
    Permissions:
        Only admin users are allowed to access these endpoints.
    Parsers:
        Supports multipart/form-data and form data for file uploads.
    Logging:
        Logs successful and failed operations for auditing and debugging purposes.
    OpenAPI/Swagger:
        Each endpoint is documented with summary, description, request, and response schemas for API documentation.
    """
    queryset = EmailTemplate.objects.all().order_by('updated_at')
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAdminUser]  # Only allow admin users to access this
    # Allow file uploads via multipart/form-data
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Create Email Template",
        description="Create a new email template with HTML and plain text files, attachments, images, and styles.",
        request=EmailTemplateSerializer,
        responses={
            201: EmailTemplateSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email template created successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email template created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        logger.error(f"Email template creation failed: {serializer.errors}")
        return Response(
            {
                "message": "Email template creation failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Update Email Template",
        description="Update an existing email template. Partial updates are allowed.",
        request=EmailTemplateSerializer,
        responses={
            200: EmailTemplateSerializer,
            400: "Bad Request"
        }
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email template updated successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email template updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        logger.error(f"Email template update failed: {serializer.errors}")
        return Response(
            {
                "message": "Email template update failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Retrieve Email Template",
        description="Retrieve a specific email template by ID.",
        responses={
            200: EmailTemplateSerializer,
            404: "Not Found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Email template retrieved successfully: {serializer.data}")
        return Response(
            {
                "message": "Email template retrieved successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete Email Template",
        description="Delete a specific email template by ID.",
        responses={
            204: "No Content",
            404: "Not Found"
        }
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        html_path = instance.html_file.path if instance.html_file else None
        plain_path = instance.plain_text_file.path if instance.plain_text_file else None
        attachment_paths = [a.file.path for a in instance.attachments.all()]
        image_paths = [i.image.path for i in instance.images.all()]
        style_paths = [s.style_file.path for s in instance.styles.all()]
    
        instance.delete()
        # Trigger the Celery task to delete files
        delete_email_task.delay(
            html_path, plain_path,
            attachment_paths, image_paths,
            style_paths
        )

        logger.info(f"Email template deleted successfully: {instance.id}")
        return Response(
            {
                "message": "Email template deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )

class EmailAttachmentViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing email attachments associated with email templates.
    This viewset provides endpoints to create, update, retrieve, and delete email attachments.
    It supports multipart and form data uploads, and logs all operations for auditing purposes.
    Endpoints:
        - create: Create a new email attachment.
        - update: Update an existing email attachment (partial updates allowed).
        - retrieve: Retrieve a specific email attachment by ID.
        - destroy: Delete a specific email attachment by ID.
    Attributes:
        queryset (QuerySet): Queryset of all EmailAttachment objects, ordered by 'updated_at'.
        serializer_class (Serializer): Serializer class for email attachments.
        parser_classes (list): List of parsers to handle multipart and form data.
    Schema:
        Each endpoint is documented with OpenAPI schema for better API documentation and client generation.
    """

    queryset = EmailAttachment.objects.all().order_by('updated_at')
    serializer_class = EmailAttachmentSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Create Email Attachment",
        description="Create a new email attachment associated with an email template.",
        request=EmailAttachmentSerializer,
        responses={
            201: EmailAttachmentSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email attachment created successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email attachment created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        logger.error(f"Email attachment creation failed: {serializer.errors}")
        return Response(
            {
                "message": "Email attachment creation failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Update Email Attachment",
        description="Update an existing email attachment. Partial updates are allowed.",
        request=EmailAttachmentSerializer,
        responses={
            200: EmailAttachmentSerializer,
            400: "Bad Request"
        }
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email attachment updated successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email attachment updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        logger.error(f"Email attachment update failed: {serializer.errors}")
        return Response(
            {
                "message": "Email attachment update failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Retrieve Email Attachment",
        description="Retrieve a specific email attachment by ID.",
        responses={
            200: EmailAttachmentSerializer,
            404: "Not Found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Email attachment retrieved successfully: {serializer.data}")
        return Response(
            {
                "message": "Email attachment retrieved successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete Email Attachment",
        description="Delete a specific email attachment by ID.",
        responses={
            204: "No Content",
            404: "Not Found"
        }
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        logger.info(f"Email attachment deleted successfully: {instance.id}")
        return Response(
            {
                "message": "Email attachment deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )

class EmailImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing EmailImage objects.
    This ViewSet provides endpoints to create, update, retrieve, and delete email images associated with email templates.
    It supports multipart and form data uploads for image handling and uses the EmailImageSerializer for serialization.
    Endpoints:
        - create: Create a new email image.
        - update: Update an existing email image (partial updates allowed).
        - retrieve: Retrieve a specific email image by ID.
        - destroy: Delete a specific email image by ID.
    All endpoints return structured responses with a message and relevant data or errors.
    Logging is performed for all operations to track success and failure events.
    """
    queryset = EmailImage.objects.all().order_by('updated_at')
    serializer_class = EmailImageSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Create Email Image",
        description="Create a new email image associated with an email template.",
        request=EmailImageSerializer,
        responses={
            201: EmailImageSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email image created successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email image created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        logger.error(f"Email image creation failed: {serializer.errors}")
        return Response(
            {
                "message": "Email image creation failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Update Email Image",
        description="Update an existing email image. Partial updates are allowed.",
        request=EmailImageSerializer,
        responses={
            200: EmailImageSerializer,
            400: "Bad Request"
        }
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email image updated successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email image updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        logger.error(f"Email image update failed: {serializer.errors}")
        return Response(
            {
                "message": "Email image update failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Retrieve Email Image",
        description="Retrieve a specific email image by ID.",
        responses={
            200: EmailImageSerializer,
            404: "Not Found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Email image retrieved successfully: {serializer.data}")
        return Response(
            {
                "message": "Email image retrieved successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete Email Image",
        description="Delete a specific email image by ID.",
        responses={
            204: "No Content",
            404: "Not Found"
        }
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        logger.info(f"Email image deleted successfully: {instance.id}")
        return Response(
            {
                "message": "Email image deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )

class EmailStyleViewSet(viewsets.ModelViewSet):
    """
    A viewset for managing email styles in the notification system.
    This viewset provides endpoints to create, update, retrieve, and delete email styles,
    which are associated with email templates. It supports multipart and form data parsing,
    and uses the `EmailStyleSerializer` for serialization.
    Endpoints:
        - create: Create a new email style.
        - update: Update an existing email style (partial updates allowed).
        - retrieve: Retrieve a specific email style by its ID.
        - destroy: Delete a specific email style by its ID.
    Logging:
        - Logs successful and failed operations for auditing and debugging purposes.
    Schema:
        - Uses `drf-spectacular`'s `extend_schema` for OpenAPI documentation.
    Attributes:
        queryset (QuerySet): All email styles ordered by their last update time.
        serializer_class (Serializer): The serializer used for email styles.
        parser_classes (list): Parsers for handling multipart and form data.
    """
    queryset = EmailStyle.objects.all().order_by('updated_at')
    serializer_class = EmailStyleSerializer
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Create Email Style",
        description="Create a new email style associated with an email template.",
        request=EmailStyleSerializer,
        responses={
            201: EmailStyleSerializer,
            400: "Bad Request"
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email style created successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email style created successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        logger.error(f"Email style creation failed: {serializer.errors}")
        return Response(
            {
                "message": "Email style creation failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Update Email Style",
        description="Update an existing email style. Partial updates are allowed.",
        request=EmailStyleSerializer,
        responses={
            200: EmailStyleSerializer,
            400: "Bad Request"
        }
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f"Email style updated successfully: {serializer.data}")
            return Response(
                {
                    "message": "Email style updated successfully.",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        logger.error(f"Email style update failed: {serializer.errors}")
        return Response(
            {
                "message": "Email style update failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    @extend_schema(
        summary="Retrieve Email Style",
        description="Retrieve a specific email style by ID.",
        responses={
            200: EmailStyleSerializer,
            404: "Not Found"
        }
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"Email style retrieved successfully: {serializer.data}")
        return Response(
            {
                "message": "Email style retrieved successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Delete Email Style",
        description="Delete a specific email style by ID.",
        responses={
            204: "No Content",
            404: "Not Found"
        }
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        logger.info(f"Email style deleted successfully: {instance.id}")
        return Response(
            {
                "message": "Email style deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT
        )

@extend_schema(
    summary="Admin Send Email",
    description="Send an email using a specified template. This endpoint is restricted to admin users.",
    request=AdminSendEmailSerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Confirmation message indicating the email was sent successfully.",
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "uri",
                        "description": "URLs of the attachments included in the email."
                    },
                },
                "styles": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "uri",
                        "description": "URLs of the styles applied to the email."
                    },
                },
                "images": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "uri",
                        "description": "URLs of the images included in the email."
                    },
                },
            },
        },
        400: "Bad Request",
        403: "Forbidden",
        404: "Not Found",
    }
)
class AdminSendEmailView(APIView):
    """
    APIView for admin users to send emails using a specified template.
    This view allows an admin to send an email to a specified recipient using a selected email template.
    It validates the input data using `AdminSendEmailSerializer`, retrieves all related attachments, styles,
    and images from the template, and triggers an asynchronous email sending task. The response includes
    confirmation of the sent email along with URLs for the attachments, styles, and images used.
    Methods:
        post(request):
            Validates the request data, fetches template resources, triggers the email sending task,
            and returns a response with details about the sent email and associated resources.
    Permissions:
        Only accessible to admin users (`IsAdminUser`).
    """
    permission_classes = [IsAdminUser]
    serializer_classes = AdminSendEmailSerializer

    def post(self, request):
        serializer = AdminSendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        template = serializer.validated_data['template_id']

        # Fetch all related attachments, styles, and images
        attachments = template.attachments.all()
        styles = template.styles.all()
        images = template.images.all()

        # All email send by this endpoint with no context
        send_email_task.delay(
            subject=template.subject,
            template_name=template.name,
            context={},
            recipient_list=[email],
            attachments=[a.file.path for a in attachments]
        )

        return Response({
            "message": f"Email sent to {email} using template '{template.name}'.",
            "attachments": [a.file.url for a in attachments],
            "styles": [s.style_file.url for s in styles],
            "images": [i.image.url for i in images],
        }, status=200)

@extend_schema(
    summary="Group Targeting",
    description="Segment users based on specified filters and grouping criteria. This endpoint allows the admin to specify filters and grouping criteria to segment users. It validates the input data, applies the specified filters, and groups the users accordingly.",
    request=GroupTargetingSerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Confirmation message indicating the users were grouped successfully.",
                },
                "data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field_name": {
                                "type": "string",
                                "description": "The name of the field used for grouping."
                            },
                            "count": {
                                "type": "integer",
                                "description": "The number of users in this group."
                            },
                            "template_id": {
                                "type": "integer",
                                "description": "The ID of the email template used for this group."
                            }
                        }
                    },
                    "description": "List of grouped user data based on the specified filters and grouping criteria."
                }
            },
        },
        400: "Bad Request",
        403: "Forbidden",
    }
)
class GroupTargetingView(APIView):
    def post(self, request):
        serializer = GroupTargetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        filters = serializer.validated_data['filters']
        group_by = serializer.validated_data['group_by']

        qs = User.objects.filter(**filters).values('email', *group_by)
        grouped = defaultdict(lambda: {"count": 0, "emails": []})

        template = serializer.validated_data['template_id']

        # Fetch all related attachments, styles, and images
        attachments = template.attachments.all()
        styles = template.styles.all()
        images = template.images.all()

        for user in qs:
            key = tuple(user[field] for field in group_by)
            grouped[key]["count"] += 1
            grouped[key]["emails"].append(user["email"])

        data = []
        for key, value in grouped.items():
            group_dict = dict(zip(group_by, key))
            group_dict["count"] = value["count"]
            group_dict["emails"] = value["emails"]
            group_dict["template_id"] = template.id
            data.append(group_dict)

            # --- BULK EMAIL SENDING ---
            # You can customize subject, template, and context as needed per group
            # Send email to all emails in this group (asynchronously)
            send_email_task.delay(
                subject=template.subject,
                template_name=template.name,
                context={},
                recipient_list=group_dict["emails"],
                attachments=[a.file.path for a in attachments]
            )

        return Response({
            "message": "Users grouped successfully.",
            "data": data
        }, status=status.HTTP_200_OK)



@extend_schema(
    summary="Newsletter Subscription",
    description="Allows authenticated users to subscribe or unsubscribe from the newsletter. This endpoint accepts a boolean field 'subscribe' in the request body to indicate whether the user wants to subscribe (true) or unsubscribe (false) from the newsletter. The user's subscription status is updated accordingly.",
    request=NewsletterSubscriptionSerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Confirmation message indicating the user's subscription status has been updated.",
                }
            },
        },
        400: "Bad Request",
        403: "Forbidden",
    }
)
class NewsletterSubscriptionView(APIView):
    """
    API view to handle newsletter subscription for authenticated users.
    Allows users to subscribe or unsubscribe from the newsletter by sending a POST request.
    The request body should contain a boolean field 'subscribe'. The user's subscription
    status is updated accordingly.
    Permissions:
        - Only authenticated users can access this view.
    Throttling:
        - Scoped rate throttling is applied with the scope 'newsletter-subscription'.
    Methods:
        post(request):
            Updates the user's newsletter subscription status based on the 'subscribe' field
            in the request data. Returns a message indicating the new subscription status.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'newsletter-subscription'

    def post(self, request):
        serializer = NewsletterSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscribe = serializer.validated_data['subscribe']
        user = request.user
        user.is_subscribed = subscribe
        user.save()
        return Response(
        {
            "message": "Subscribed to newsletter." if subscribe else "Unsubscribed from newsletter."
        },
        status=status.HTTP_200_OK
)



@extend_schema(
    summary="Schedule Newsletter",
    description=(
        "Allows admin users to schedule a newsletter email to all subscribed users. "
        "Provide the email template ID and the scheduled time (in ISO 8601 UTC format). "
        "The newsletter will be sent to all users who are subscribed at the specified time."
    ),
    request=ScheduleNewsletterSerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Confirmation message indicating the newsletter was scheduled."
                }
            }
        },
        400: "Bad Request",
        403: "Forbidden"
    }
)
class ScheduleNewsletterView(APIView):
    """
    API view to schedule a newsletter for future delivery.
    This view allows admin users to schedule a newsletter to be sent at a specified time.
    It expects a POST request with the newsletter template ID and the scheduled time.
    Upon validation, it schedules a Celery task to send the newsletter at the desired time.
    Methods:
        post(request):
            Schedules the newsletter sending task using the provided template ID and scheduled time.
            Returns a confirmation message upon successful scheduling.
    Permissions:
        Only accessible by admin users.
    """

    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = ScheduleNewsletterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        template = serializer.validated_data['template_id']
        scheduled_time = serializer.validated_data['scheduled_time']

        # Schedule the Celery task
        send_newsletter_task.apply_async(
            args=[template.id],
            eta=scheduled_time
        )

        return Response(
        {
            "message": f"Newsletter scheduled to be sent at {scheduled_time}."
        }
        , status=status.HTTP_200_OK
        )
