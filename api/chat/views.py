from django.core.cache import cache
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import ChatMessage
from .serializers import ChatMessageSerializer
from django.contrib.auth import get_user_model
import logging
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes

User = get_user_model()
logger = logging.getLogger("chat_views")

# TODO: Fixed the OpenAPI schema generation for the ChatHistoryView and ChatContactsView
# @extend_schema(
#     summary="Chat history between authenticated user and a customer",
#     description="Retrieve the chat history (all messages) between the authenticated user and a specified customer. Returns user info for both parties and a list of serialized messages.",
#     parameters=[
#         OpenApiParameter(
#             name="customer_id",
#             type=OpenApiTypes.INT,
#             location=OpenApiParameter.QUERY,
#             required=True,
#             description="ID of the customer to fetch chat history with"
#         ),
#     ],
#     responses={
#         200: OpenApiResponse(
#             response={
#                 "chat_between": {
#                     "owner": {
#                         "id": OpenApiTypes.INT,
#                         "name": OpenApiTypes.STR,
#                         "image_url": OpenApiTypes.STR
#                     },
#                     "customer": {
#                         "id": OpenApiTypes.INT,
#                         "name": OpenApiTypes.STR,
#                         "image_url": OpenApiTypes.STR
#                     }
#                 },
#                 "messages": [
#                     {
#                         "id": OpenApiTypes.INT,
#                         "sender_id": OpenApiTypes.INT,
#                         "receiver_id": OpenApiTypes.INT,
#                         "message": OpenApiTypes.STR,
#                         "timestamp": OpenApiTypes.STR,
#                         "is_read": OpenApiTypes.BOOL
#                     }
#                 ]
#             },
#             description="Chat history and user info returned successfully."
#         ),
#         400: OpenApiResponse(description="customer_id is required."),
#         404: OpenApiResponse(description="Customer not found."),
#         500: OpenApiResponse(description="An error occurred while fetching chat history."),
#     }
# )
class ChatHistoryView(APIView):
    """
    Retrieve the chat history (all messages) between the authenticated user and a specified customer.

    - Requires `customer_id` as a query parameter.
    - Returns user info for both parties and a list of serialized messages.
    - 200: Success, chat history and user info.
    - 400: customer_id missing.
    - 404: Customer not found.
    - 500: Server error.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Handles GET requests to fetch chat history between the authenticated user and a customer.
        """
        try:
            customer_id = request.GET.get("customer_id")
            owner = request.user

            if not customer_id:
                logger.warning("customer_id not provided in request.")
                return Response({"error": "customer_id is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                customer = User.objects.get(id=customer_id)
            except User.DoesNotExist:
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

# @extend_schema(
#     summary="Chat contacts for the authenticated user",
#     description="Returns a list of users the authenticated user has chatted with, including unread message count, online status, last seen, and last message.",
#     responses={
#         200: OpenApiResponse(
#             response={
#                 "user_id": OpenApiTypes.INT,
#                 "chats": [
#                     {
#                         "contact_id": OpenApiTypes.INT,
#                         "contact_name": OpenApiTypes.STR,
#                         "contact_img": OpenApiTypes.STR,
#                         "last_message": OpenApiTypes.STR,
#                         "timestamp": OpenApiTypes.STR,
#                         "unread_count": OpenApiTypes.INT,
#                         "online": OpenApiTypes.BOOL,
#                         "last_seen": OpenApiTypes.STR
#                     }
#                 ]
#             },
#             description="List of chat contacts returned successfully."
#         ),
#         500: OpenApiResponse(description="An error occurred while fetching chat contacts."),
#     }
# )
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

            return Response({
                "user_id": user.id,
                "chats": list(contacts.values())
            })
        except Exception as e:
            logger.error(f"Error in ChatContactsView.get: {e}")
            return Response({"error": "An error occurred while fetching chat contacts."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
