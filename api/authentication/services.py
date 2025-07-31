# services.py
import requests, logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from .utils import generate_jwt_tokens
from .models import VerificationCode
from accounts.models import BusinessOwner
from stores.models import Store
import random
import string

# Get the user model
User = get_user_model()
# Create the logger
logger = logging.getLogger("authentication_services")


class AuthenticationService:
    """Service class for authentication operations"""
    
    @staticmethod
    def send_verification_code(user, code_type='phone'):
        """Send verification code to user"""
        # Generate a 6-digit code
        code = ''.join(random.choices(string.digits, k=6))
        
        # Create verification code record
        verification_code = VerificationCode.objects.create(
            user=user,
            code=code,
            code_type=code_type,
            expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )
        
        # Here you would integrate with SMS/Email service
        # For now, we'll just log it
        logger.info(f"Verification code {code} sent to user {user.email}")
        
        return {
            'success': True,
            'message': 'Verification code sent successfully',
            'code_id': verification_code.id
        }
    
    @staticmethod
    def verify_code(user, code, code_type='phone'):
        """Verify the code provided by user"""
        try:
            verification_code = VerificationCode.objects.get(
                user=user,
                code=code,
                code_type=code_type,
                is_used=False
            )
            
            if verification_code.is_expired():
                return {
                    'success': False,
                    'message': 'Verification code has expired'
                }
            
            # Mark code as used
            verification_code.is_used = True
            verification_code.save()
            
            # Mark user as verified (active)
            user.is_active = True
            user.save()
            
            return {
                'success': True,
                'message': 'Code verified successfully'
            }
            
        except VerificationCode.DoesNotExist:
            return {
                'success': False,
                'message': 'Invalid verification code'
            }
    
    @staticmethod
    def check_user_auth_status(user):
        """Check authentication status of user"""
        return {
            'is_authenticated': user.is_authenticated if hasattr(user, 'is_authenticated') else False,
            'is_active': user.is_active,
            'is_verified': user.is_active,  # Using is_active as is_verified equivalent
            'can_login': user.is_active,
            'phone_verified': getattr(user, 'phone_verified', False),
            'email_verified': getattr(user, 'email_verified', False)
        }
    
    @staticmethod
    def mask_phone_number(phone_number):
        """Mask phone number for privacy"""
        if not phone_number:
            return ""
        
        # Convert PhoneNumber to string if needed
        phone_str = str(phone_number)
        
        # Keep first 3 and last 2 digits, mask the rest
        if len(phone_str) > 5:
            masked = phone_str[:3] + '*' * (len(phone_str) - 5) + phone_str[-2:]
            return masked
        return phone_str


def send_sms(phone_number, message):
    """Send SMS function (placeholder for external service integration)"""
    logger.info(f"SMS sent to {phone_number}: {message}")
    return True


def send_email(email, subject, message):
    """Send email function (placeholder for external service integration)"""
    logger.info(f"Email sent to {email} with subject '{subject}': {message}")
    return True


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
