import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
import logging

User = get_user_model()
logger = logging.getLogger("middlewares")

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])
        auth_header = headers.get(b'authorization')

        if auth_header:
            try:
                token = auth_header.decode().split()[1] # Extract token from "Bearer <token>"
                payload = jwt.decode(
                    token,
                    settings.SIMPLE_JWT['SIGNING_KEY'],
                    algorithms=[settings.SIMPLE_JWT['ALGORITHM']],
                )
                user_id = payload.get("user_id")
                if user_id:
                    scope["user"] = await get_user(user_id)
                else:
                    scope["user"] = AnonymousUser()
            except (jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError, KeyError) as e:
                logger.warning(f"JWT authentication failed: {e}")
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)