from django.core.cache import cache
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import ChatMessage
from .serializers import ChatMessageSerializer, ChatHistorySerializer, ChatContactsSerializer
from django.contrib.auth import get_user_model
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

User = get_user_model()
logger = logging.getLogger("chat_views")

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="customer_id",
            type=int,
            location=OpenApiParameter.QUERY,
            required=True,
            description="ID of the customer to fetch chat history with.",
        )
    ],
    responses={
        200: OpenApiResponse(description="Chat history and user info retrieved successfully."),
        400: OpenApiResponse(description="Missing or invalid customer_id."),
        500: OpenApiResponse(description="Server error while retrieving chat history."),
    },
    summary="Get Chat History",
    description="Returns the chat history between the authenticated user and the specified customer, including user info and messages.",
)
class ChatHistoryView(APIView):
    """
    Retrieve the chat history (all messages) between the authenticated user and a specified customer.

    - Requires `customer_id` as a query parameter.
    - Returns user info for both parties and a list of serialized messages.
    - 200: Success, chat history and user info.
    - 400: customer_id missing.
    - 500: Server error.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to fetch chat history between the authenticated user and a customer.
        """
        try:
            serializer = ChatHistorySerializer(data=request.GET)
            
            if not serializer.is_valid():
                logger.error(f"Validation error: {serializer.errors}")
                return Response({"error":serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

            customer_id = serializer.validated_data['customer_id']
            owner = request.user

            try:
                customer = User.objects.get(id=customer_id)
            except User.DoesNotExist:
                # already validated in serializer, this is just for safety
                logger.error(f"Customer with id {customer_id} does not exist.")
                return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

            messages = ChatMessage.objects.filter(
                sender_id__in=[owner.id, customer_id],
                receiver_id__in=[owner.id, customer_id]
            ).order_by("timestamp")

            logger.info(f"Fetched chat history between user {owner.id} and customer {customer_id}.")

            return Response({
                "chat_between": {
                    "owner": {
                        "id": owner.id,
                        "name": owner.get_full_name(),
                        "image_url": owner.profile_picture.url if getattr(owner, "profile_picture", None) and getattr(owner.profile_picture, "name", None) else None
                    },
                    "customer": {
                        "id": customer.id,
                        "name": customer.get_full_name(),
                        "image_url": customer.profile_picture.url if getattr(customer, "profile_picture", None) and getattr(customer.profile_picture, "name", None) else None
                    }
                },
                "messages": ChatMessageSerializer(messages, many=True).data
            })
        except Exception as e:
            logger.error(f"Error in ChatHistoryView.get: {e}")
            return Response({"error": "An error occurred while fetching chat history."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@extend_schema(
    responses={
        200: OpenApiResponse(description="List of chat contacts retrieved successfully."),
        500: OpenApiResponse(description="Server error while retrieving chat contacts."),
    },
    summary="Get Chat Contacts",
    description="Returns a list of contacts the authenticated user has chatted with, including unread message count, online status, last seen, and last message.",
)
class ChatContactsView(APIView):
    """
    Retrieve a list of chat contacts for the authenticated user.

    - Each contact includes user info, unread message count, online status, last seen, and last message.
    - 200: Success, list of chat contacts.
    - 500: Server error.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to fetch chat contacts for the authenticated user.
        """
        try:
            user = request.user
            messages = ChatMessage.objects.filter(Q(sender=user) | Q(receiver=user))

            contacts = {}
            for msg in messages.order_by('-timestamp'):
                contact = msg.receiver if msg.sender == user else msg.sender
                if contact.id not in contacts:
                    unread = ChatMessage.objects.filter(sender=contact, receiver=user, is_read=False).count()

                    # Get online status and last seen from cache
                    online_key = f"user_online_{contact.id}"
                    last_seen_key = f"user_last_seen_{contact.id}"

                    is_online = cache.get(online_key, False)
                    last_seen = cache.get(last_seen_key)

                    contacts[contact.id] = {
                        "contact_id": contact.id,
                        "contact_name": contact.get_full_name(),
                        "contact_img": contact.profile_picture.url if contact.profile_picture else None,
                        "last_message": msg.message,
                        "timestamp": msg.timestamp,
                        "unread_count": unread,
                        "online": is_online,
                        "last_seen": last_seen
                    }

            logger.info(f"Fetched chat contacts for user {user.id}.")

            serializer = ChatContactsSerializer(data=list(contacts.values()), many=True)
            serializer.is_valid(raise_exception=True)

            return Response({
                "user_id": user.id,
                "chats": serializer.data
            })
        except Exception as e:
            logger.error(f"Error in ChatContactsView.get: {e}")
            return Response({"error": "An error occurred while fetching chat contacts."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)