# services.py
import requests, logging
from django.conf import settings
from django.contrib.auth import get_user_model
from .utils import generate_jwt_tokens
from ..accounts.models import BusinessOwner
from ..stores.models import Store

# Get the user model
User = get_user_model()
# Create the logger
logger = logging.getLogger("authentication_services")


def authenticate_google_user(code: str, state: str):
    # Call Google's token endpoint to exchange the code for tokens
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code, "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }).json()

    # Check if the response contains an access token
    if not resp.get("access_token"):
        logger.error("Google token exchange failed: %s", resp)
        raise ValueError(resp.get("error_description") or "Token error")

    # Get the user info
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {resp['access_token']}"}
    ).json()
    email = userinfo.get("email")
    if not email:
        logger.error("Google userinfo missing email: %s", userinfo)
        raise ValueError("Email missing")

    # Determine account type from state (e.g., "accountType=seller" or "accountType=buyer")
    account_type = None
    if state and state.startswith("accountType="):
        account_type = state.split("=")[1]

    # Prepare user creation defaults
    user_defaults = {
        "first_name": userinfo.get("given_name", ""),
        "last_name": userinfo.get("family_name", ""),
        "is_store_owner": account_type == "seller",
        "account_type": account_type if account_type in ("seller", "buyer") else "buyer",
    }

    # Create or get the user
    user, created = User.objects.get_or_create(
        email=email,
        defaults=user_defaults
    )

    # If seller, ensure BusinessOwner profile exists
    if account_type == "seller":
        if created or not hasattr(user, "business_owner_profile"):
            # Create a placeholder store if needed
            store, _ = Store.objects.get_or_create(
                name=f"{userinfo.get('given_name', '')}'s Store",
                defaults={"owner": user}
            )
            BusinessOwner.objects.get_or_create(user=user, store=store)

    # Generate tokens
    tokens = generate_jwt_tokens(user)
    account = account_type

    return user, tokens, created, account


def set_account_type_for_user(user, account_type: str):
    """
    Maps account_type string to is_store_owner boolean.
    """
    if account_type == "seller":
        user.is_store_owner = True
    else:
        user.is_store_owner = False
    user.save()
