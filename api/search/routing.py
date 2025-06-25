from django.urls import path
from .consumers import AutocompleteConsumer

websocket_urlpatterns = [
    path('ws/autocomplete/', AutocompleteConsumer.as_asgi()),
]