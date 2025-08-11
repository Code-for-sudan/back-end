from urllib.parse import parse_qs
import jwt
import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()
logger = logging.getLogger("middlewares")

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JwtAuthMiddleware(BaseMiddleware):
    """
    JWT middleware using ?token=<access_token> query parameter
    """

    async def __call__(self, scope, receive, send):
        # Get query string from scope
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token_list = query_params.get("token", [])
        token = token_list[0] if token_list else None

        if token:
            try:
                # Validate token
                UntypedToken(token)

                # Decode token
                payload = jwt.decode(
                    token,
                    settings.SIMPLE_JWT.get("SIGNING_KEY", settings.SECRET_KEY),
                    algorithms=[settings.SIMPLE_JWT.get("ALGORITHM", "HS256")],
                )

                user_id = payload.get("user_id")
                if user_id:
                    scope["user"] = await get_user(user_id)
                else:
                    scope["user"] = AnonymousUser()

            except (InvalidToken, TokenError, jwt.InvalidTokenError, KeyError) as e:
                logger.warning(f"JWT validation failed: {e}")
                scope["user"] = AnonymousUser()
        else:
            logger.info("Token query parameter missing or invalid.")
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)
