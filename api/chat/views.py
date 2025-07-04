from django.core.cache import cache
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ChatMessage
from .serializers import ChatMessageSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        customer_id = request.GET.get("customer_id")
        owner = request.user

        messages = ChatMessage.objects.filter(
            sender_id__in=[owner.id, customer_id],
            receiver_id__in=[owner.id, customer_id]
        ).order_by("timestamp")

        customer = User.objects.get(id=customer_id)

        return Response({
            "chat_between": {
                "owner": {
                    "id": owner.id,
                    "name": owner.get_full_name(),
                    "image_url": owner.profile_picture.url if owner.profile_picture else None
                },
                "customer": {
                    "id": customer.id,
                    "name": customer.get_full_name(),
                    "image_url": customer.profile_picture.url if customer.profile_picture else None
                }
            },
            "messages": ChatMessageSerializer(messages, many=True).data
        })

class ChatContactsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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

        return Response({
            "user_id": user.id,
            "chats": list(contacts.values())
        })
