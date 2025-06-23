import requests, logging
from rest_framework import status # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from accounts.serializers import UserSerializer
from .utils import generate_jwt_tokens
from notifications.utils import send_email_with_attachments
from .serializers import (LoginSerializer, ResetPasswordConfirmSerializer, GoogleAuthCodeSerializer,
                          ResetPasswordVerifyRequestSerializer, ResetPasswordConfirmRequestSerializer,
                          ResetPasswordRequestSerializer
                        )

# Create a logger for this module
logger = logging.getLogger('authentication_views')

# Get the user model
User = get_user_model()

@extend_schema(
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(
            description='Login successful. Returns user data and access token.'
        ),
        400: OpenApiResponse(
            description='Invalid email or password.'
        ),
    },
    summary="User Login",
    description="Authenticates user using email and password. Returns JWT access token and sets refresh token as HttpOnly cookie.",
    examples=[
        OpenApiExample(
            name="Login example",
            value={"email": "user@example.com", "password": "your_password"},
            request_only=True,
            response_only=False
        ),
        OpenApiExample(
            name="Successful login response",
            value={
                "message": "Login successful.",
                "user": {
                    "id": "1234",
                    "email": "user@example.com",
                    "first_name": "John"
                },
                "access_token": "eyJ0eXAiOiJKV1QiLCJh..."
            },
            request_only=False,
            response_only=True
        ),
    ]
)
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        """
        Handles user login by validating email and password.
        This function authenticates the user and returns a JWT token if successful.
        Args:
            request (HttpRequest): The HTTP request object containing the user's email and password.
        Returns:
            Response: A DRF Response object containing the login status, user data, and access token.
                If authentication fails, an error message is returned.
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            access_token, refresh_token = generate_jwt_tokens(user)

            response = Response(
                {
                    'message': 'Login successful.',
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'first_name': user.first_name,
                    },
                    'access_token': access_token,
                },
                status=status.HTTP_200_OK
            )

            response.set_cookie(
                key="refresh_token",
                value=str(refresh_token),
                httponly=True,
                secure=True,
                samesite="Lax",
            )
            return response

        logger.error(f"Login failed for {request.data.get('email')}: {serializer.errors}")
        return Response(
            {'message': 'Invalid email or password.'},
            status=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(
    summary="Initiate Google OAuth2 login",
    description="Redirects the user to Google OAuth2 consent screen for authentication.",
    responses={
        302: OpenApiResponse(description="Redirects to Google OAuth2 login page"),
    },
)
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
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


@extend_schema(
    request=GoogleAuthCodeSerializer,
    responses={
        200: OpenApiResponse(description="Google login successful. Returns user data and JWT access token."),
        400: OpenApiResponse(description="Error during authentication process (e.g., missing code or failed token exchange)."),
    },
    summary="Google OAuth2 Callback",
    description="Handles the Google OAuth2 callback. Exchanges code for tokens, retrieves user info, logs in or creates user, and sets JWT tokens.",
    examples=[
        OpenApiExample(
            name="Authorization Code Request",
            value={"code": "4/0AY0e-g7a_example_code"},
            request_only=True
        ),
        OpenApiExample(
            name="Successful Response",
            value={
                "message": "Login successful.",
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "first_name": "Jane",
                    "last_name": "Doe"
                },
                "access_token": "eyJ0eXAiOiJKV1QiLCJh..."
            },
            response_only=True
        )
    ]
)
class GoogleCallbackView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
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
        code = request.data.get("code")

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
        access_token_jwt, refresh_token = generate_jwt_tokens(user)

        # Serialize the user data
        user_serializer = UserSerializer(user)

        response = Response(
            {
                'message': 'Login successful.',
                'user': user_serializer.data,
                'access_token': access_token_jwt,
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



@extend_schema(
    summary="Request password reset OTP resend",
    description="Sends a new OTP code to the user's email to allow password reset.",
    request=ResetPasswordRequestSerializer,
    responses={
        200: OpenApiResponse(description="OTP has been resent to the user's email."),
        400: OpenApiResponse(description="Missing email or user does not exist."),
    }
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email'].strip().lower()
        if not email:
            logger.error("No email provided for OTP resend.")
            return Response(
                {
                    'message': 'Email is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # If the user does not exist, we still return a success message to prevent email enumeration
            # This is a security measure to avoid revealing whether an email is registered or not.
            logger.warning(f"User with email {email} does not exist.")
            return Response(
                {
                    'message': 'If this email is registered, an OTP has been sent to it.'
                },
                status=status.HttP_200_OK
            )
        # Create the email context
        subject = "[Attention] Password Reset OTP"
        template_name = "reset_password_otp"
        recipient_list = [user.email]
        attachments = None  # No attachments needed for OTP resend
        context = {
            'user': user,
            'otp_code': user.generate_otp()
        }
        # Send the email with OTP
        send_email_with_attachments.delay(
            subject=subject,
            template_name=template_name,
            context=context,
            recipient_list=recipient_list,
            attachments=attachments
        )

        logger.info(f"OTP sent to user {email}.")
        return Response(
            {
                'message': 'OTP has been sent to your email.'
            },
            status=status.HTTP_200_OK
        )


@extend_schema(
   
)
class ResetPasswordrequestVerifyView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        """
        Handles OTP verification for user login.
        This function verifies the OTP (One-Time Password) provided by the user
        and returns a response indicating the success or failure of the verification.
        If successful, it generates JWT tokens for the user and sets a refresh token
        as an HTTP-only cookie.
        Args:
            request (Request): The HTTP request object containing the user's email
                               and OTP code in the request data.
        Returns:
            Response: A Django REST framework Response object with the following:
                - HTTP 200 OK: If the OTP verification is successful, returns a success
                  message, access token, and user details.
                - HTTP 400 Bad Request: If the email or OTP code is missing, or if the
                  OTP code is invalid.
                - HTTP 404 Not Found: If no user is found with the provided email.
        Side Effects:
            - Sets a secure, HTTP-only cookie for the refresh token with a 1-day expiration.
        Raises:
            None
        """

        user_email = request.data.get('email', '').strip().lower()
        otp_code = request.data.get('otp_code')
        if not user_email or not otp_code:
            logger.error(f"Missing email or OTP in request: {request.data}")
            return Response(
                {'message': 'Email and OTP code are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(email=user_email).first()
        if not user:
            logger.warning("Un email was sent to the user.")
            return Response(
                {'message': f'User for email: "{user_email}" not found.'},
                status=status.HTTP_200_OK
            )

        if not user.verify_otp(otp_code):
            logger.warning(f"Invalid OTP for user {user_email}")
            return Response(
                {'message': 'Invalid OTP code.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        access_token, refresh_token = generate_jwt_tokens(user)
        response = Response(
            {
                'message': 'Login successful.',
                'access_token': access_token,
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'first name': user.first_name,
                }
            },
            status=status.HTTP_200_OK
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh_token),
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=1 * 24 * 60 * 60,  # 1 day
            path='/api/auth/'
        )

        return response
