from django.urls import path
from .views import ChatHistoryView, ChatContactsView

urlpatterns = [
    path("history", ChatHistoryView.as_view(), name="chat-history"),
    path("contacts", ChatContactsView.as_view(), name="chat-contacts"),
]
