# services.py
import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from .utils import generate_jwt_tokens

User = get_user_model()

def authenticate_google_user(code: str, state: str):
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code, "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }).json()
    if not resp.get("access_token"):
        raise ValueError(resp.get("error_description") or "Token error")

    userinfo = requests.get("https://www.googleapis.com/oauth2/v2/userinfo",
                            headers={"Authorization": f"Bearer {resp['access_token']}"}
    ).json()
    email = userinfo.get("email")
    if not email: raise ValueError("Email missing")

    user, created = User.objects.get_or_create(email=email, defaults={
        "first_name": userinfo.get("given_name", ""),
        "last_name": userinfo.get("family_name", ""),
    })
    user_data = generate_jwt_tokens(user)
    tokens = user_data  # (access, refresh)
    account = None
    if created and state and state.startswith("accountType="):
        account = state.split("=")[1]

    return user, tokens, created, account


def set_account_type_for_user(user, account_type: str):
    user.account_type = account_type
    user.save()
