import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

import django

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from .middleware import JwtAuthMiddleware
import search.routing
import chat.routing


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JwtAuthMiddleware(
        URLRouter(search.routing.websocket_urlpatterns + chat.routing.websocket_urlpatterns)),
})
