import requests, logging
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.decorators import api_view
from rest_framework import status # type: ignore
from django.conf import settings
from django.shortcuts import redirect
from .serializers import UserSerializer
from .utils import generate_jwt_tokens

# Create a logger for this module
logger = logging.getLogger('authentication')

# Get the user model
User = get_user_model()

@api_view(['GET'])
def google_login(request):
    """
    Redirect user to Google's OAuth 2.0 authentication page.
    """
    google_url = (
        "https://accounts.google.com/o/oauth2/auth"
        "?response_type=code"
        f"&client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        "&scope=email%20profile"
    )
    return redirect(google_url)



@api_view(['POST'])
def google_callback(request):
    """
    Handles the Google OAuth2 callback to authenticate a user.
    This function processes the authorization code returned by Google, exchanges it
    for an access token, retrieves user information, and either logs in the user
    or creates a new user account. It also generates JWT tokens for the user and
    sets the refresh token as an HTTP-only cookie.
    Args:
        request (HttpRequest): The HTTP request object containing the authorization
                               code in the query parameters.
    Returns:
        Response: A DRF Response object containing the login status, user data,
                  and access token. If an error occurs, an appropriate error
                  message and status code are returned.
    Workflow:
        1. Extract the authorization code from the query parameters.
        2. Exchange the authorization code for an access token using Google's token endpoint.
        3. Use the access token to fetch the user's profile information from Google.
        4. Check if the user exists in the database; if not, create a new user.
        5. Generate JWT tokens (access and refresh) for the user.
        6. Return the user data and access token in the response, and set the refresh
           token as an HTTP-only cookie.
    Raises:
        KeyError: If required settings like GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET
                  are missing.
        Exception: If there are issues with the token exchange or user creation.
    Notes:
        - Ensure that the `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correctly
          configured in the Django settings.
        - The `redirect_uri` must match the one configured in the Google API Console.
        - The `User` model is assumed to have fields for `email`, `first_name`,
          `last_name`, and a related `profile` with a `picture` field.
    """

    # Get the code from the query parameters
    code = request.GET.get("code")

    # Check if code is provided
    if not code:
        logger.error("No code provided")
        return Response(
            {
                "message": "No code provided"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get the access token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": "http://127.0.0.1:8000/api/auth/google/callback/",
    }

    token_response = requests.post(token_url, data=token_data).json()
    access_token = token_response.get("access_token")

    if not access_token:
        logger.error("Failed to obtain access token")
        return Response(
            {
                "message": "Failed to obtain access token"
            }
            , status=status.HTTP_400_BAD_REQUEST
        )

    # Fetch user info
    user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    user_info = requests.get(
        user_info_url,
        headers={
            "Authorization": "Bearer {}".format(access_token)
        }
    ).json()

    email = user_info.get("email")
    first_name = user_info.get("given_name")
    last_name = user_info.get("family_name")
    profile_picture = user_info.get("picture")

    if not email:
        logger.error("Failed to retrieve email")
        return Response(
            {
                "message": "Failed to retrieve email"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if user exists or create a new one
    user, created = User.objects.get_or_create(email=email, defaults={
        "first_name": first_name,
        "last_name": last_name,
    })

    # Update user profile picture
    if created:
        if hasattr(user, 'profile_picture'):
            user.profile_picture = profile_picture

    user.save()

    # Generate JWT Token
    access_token, refresh_token = generate_jwt_tokens(user)

    # Serialize the user data
    user_serializer = UserSerializer(user)

    response = Response(
        {
            'message': 'Login successful.',
            'user': user_serializer.data,
            'access_token': access_token,
            # 'refresh_token': refresh_token
        },
        status=status.HTTP_200_OK
    )

    # Set refresh token as an HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=str(refresh_token),
        httponly=True,  # Security feature
        secure=True,  # Use only in HTTPS
        samesite="Lax",  # Protect against CSRF
    )

    return response
