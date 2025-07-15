import requests, logging
from django.utils import timezone
from rest_framework import status # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from rest_framework.throttling import  AnonRateThrottle, ScopedRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.db import transaction
from rest_framework_simplejwt.tokens import AccessToken
from accounts.serializers import UserSerializer
from .utils import generate_jwt_tokens
from .services import authenticate_google_user
from notifications.tasks import send_email_task
from .serializers import LoginSerializer, GoogleAuthCodeSerializer, SetAccountTypeSerializer, SellerSetupSerializer
from .serializers import ResetPasswordRequestSerializer, ResetPasswordrequestVerifySerializer
from .serializers import RequestUpdatePasswordSerializer                   
                

# Create a logger for this module
logger = logging.getLogger('authentication_views')

# Get the user model
User = get_user_model()

@extend_schema(
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(description="Login successful; returns user and access token."),
        400: OpenApiResponse(description="Invalid credentials."),
    },
    summary="User Login",
)
class LoginView(APIView):
    """
    LoginView handles user authentication via POST requests.
    This view allows any user to attempt login and applies rate throttling to anonymous requests.
    On successful authentication, it returns a success message, serialized user data, and a JWT access token.
    A refresh token is set in an HTTP-only cookie for secure session management.
    If authentication fails, it logs the error and returns a failure message along with serializer errors.
    Methods:
        post(request): Authenticates the user and returns JWT tokens if credentials are valid.
    """

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            access_token, refresh_token = generate_jwt_tokens(user)
            response = Response(
                {
                    "message": "Login successful.",
                    "user": UserSerializer(user).data,
                    "access_token": access_token,
                },
                status=status.HTTP_200_OK
            )
            response.set_cookie(
                "refresh_token", str(refresh_token),
                httponly=True, secure=not settings.DEBUG,
                samesite="Lax"
            )
            return response
        # Return serializer errors
        logger.error(f"Login failed for {request.data.get('email')}: {serializer.errors}")
        return Response(
            {
                "message": "Login failed.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


@extend_schema()
class GoogleLoginView(APIView):
    """
    GoogleLoginView handles the initiation of the Google OAuth 2.0 authentication flow.
    This view accepts GET requests and redirects users to Google's OAuth 2.0 authorization endpoint.
    It reads the 'accountType' query parameter to set the 'state' parameter for the OAuth request,
    allowing differentiation between user account types during authentication.
    Attributes:
        permission_classes (list): Permissions required to access this view (AllowAny).
        throttle_classes (list): Throttling applied to anonymous requests (AnonRateThrottle).
    Methods:
        get(request):
            Processes the GET request, constructs the Google OAuth URL with appropriate parameters,
            and redirects the user to Google's OAuth 2.0 server.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        # Get the user account type from query parameters
        # Redirect to Google OAuth with the appropriate parameters
        account_type = request.query_params.get("accountType")
        response_type = "code"
        client_id = settings.GOOGLE_CLIENT_ID
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        scope = "email profile"
        # Check the account_type to set-up the state
        if account_type:
            state = account_type.strip().lower()                                                                                            
        else:
            state = None

        google_url = "https://accounts.google.com/o/oauth2/auth?&response_type={}&client_id={}&redirect_uri={}&scope={}&state={}".format(
            response_type, client_id, redirect_uri, scope, state
        )
        logger.info(f"Redirecting to Google OAuth: {google_url}")
        # Instead of redirecting, return the Google OAuth URL so the frontend can handle the redirect
        return Response(
            {
                "message": "Redirect to Google OAuth",
                "google_oauth_url": google_url
            },
            status=status.HTTP_200_OK
        )


@extend_schema(
    summary="Google OAuth Callback",
    description="Handles the callback from Google OAuth after user authentication.",
    request=GoogleAuthCodeSerializer,
    responses={
        200: OpenApiResponse(description="User authenticated successfully; returns user data and tokens."),
        400: OpenApiResponse(description="Invalid or missing authorization code."),
        401: OpenApiResponse(description="Authentication failed; invalid code or user not found."),
    },
    examples=[
        OpenApiExample(
            name="Google OAuth Callback Example",
            value={
                "code": "4/0AY0e-g5...",
                "state": "accountType=seller"
            },
            request_only=True
        ),
        OpenApiExample(
            name="Successful Authentication Response",
            value={
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "isNewUser": True,
                "user": {
                    "id": "1234",
                    "email": "example@test.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "is_store_owner": True,
                        "is_store_owner": True,
                        "is_verified": True,
                        "created_at": "2024-01-01T00:00:00Z"
                    },
                    "accountType": "seller",
                    "needsAccountType": False,
                    "redirect": "/dashboard/seller-setup"
            },
            response_only=True
        )
    ]
)
        
class GoogleCallbackView(APIView):
    """
    View to handle Google OAuth callback and user authentication.
    This view processes the authorization code received from Google OAuth,
    authenticates or registers the user, and returns authentication tokens
    along with user information. It also manages account type selection for
    new users and sets a secure HTTP-only cookie for the refresh token.
    Methods
    -------
    post(request):
        Handles POST requests with the Google OAuth authorization code.
        Validates the code, authenticates the user, and returns tokens and user data.
        If the user is new, includes account type information and setup redirection.
        Sets the refresh token as an HTTP-only cookie in the response.
    Permissions
    -----------
    AllowAny: Allows any user (authenticated or not) to access this view.
    Throttling
    ----------
    AnonRateThrottle: Applies rate limiting to anonymous requests.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    
    # Get the user info from Google using the authorization code
    def get(self, request):
        serializer = GoogleAuthCodeSerializer(data=request.query_params)
        if not serializer.is_valid():
            logger.error(f"Invalid data for Google OAuth callback: {serializer.errors}")
            return Response(
            {
                "message": "Invalid or missing authorization code.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
            )

        code = serializer.validated_data["code"]
        state = serializer.validated_data.get("state")

        try:
            with transaction.atomic():
                # Authenticate the user using the provided code and state
                user, tokens, is_new, account_type = authenticate_google_user(code, state)
        except Exception as e:
            logger.error(f"Google authentication failed: {e}")
            return Response(
                {"message": "Authentication failed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prepare the response data
        resp = {
            "token": tokens[0],
            "isNewUser": is_new,
            "user": UserSerializer(user).data
        }
        
        # Check if the user is new and set account type if provided
        if is_new:
            if account_type:
                resp["accountType"] = account_type
                resp["needsAccountType"] = False
                if account_type == "seller":
                    resp["redirect"] = "/dashboard/seller-setup"
            else:
                resp["needsAccountType"] = True
        
        # Create the response object
        response = Response(resp, status=status.HTTP_200_OK)
        # Set Cookie for refresh token
        response.set_cookie(
            "refresh_token",
            str(tokens[1]),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax"
        )
        logger.info(f"Google OAuth callback successful for user {user.email}.")
        return response


@extend_schema(
    request=SetAccountTypeSerializer,
    responses={
        200: OpenApiResponse(description="Account type set successfully"),
        400: OpenApiResponse(description="Invalid or missing accountType"),
    },
    summary="Set Account Type for Google OAuth",
)
class SetAccountTypeView(APIView):
    """
    API view to set or update the account type for a user.
    POST:
        Expects a payload containing the 'account_type' field.
        Validates the input using SetAccountTypeSerializer.
        Updates the account type for the authenticated user.
        Returns a success message upon completion.
    Permissions:
        - AllowAny: Any user (authenticated or not) can access this endpoint.
    Throttling:
        - AnonRateThrottle: Applies rate limiting to anonymous users.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = SetAccountTypeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
            {
                "message": "Invalid account type.",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
            )

        account_type = serializer.validated_data["account_type"]
        user = request.user
        user.account_type = account_type
        user.is_store_owner = (account_type == "seller")
        user.save()
        return Response(
            {
                "message": "Account type updated"
                },
            status=status.HTTP_200_OK
        )


@extend_schema(
    request=SellerSetupSerializer,
    responses={
        200: OpenApiResponse(description="Seller profile completed"),
        400: OpenApiResponse(description="Validation errors"),
    },
    summary="Complete Seller Info",
)
class SellerSetupView(APIView):
    """
    APIView for handling seller setup process.
    Allows authenticated users to submit seller setup information via POST request.
    Uses SellerSetupSerializer to validate and save the data.
    Returns a success message upon completion.
    Permissions:
        - IsAuthenticated: Only authenticated users can access.
    Throttling:
        - AnonRateThrottle: Applies rate limiting for anonymous requests.
    Methods:
        post(request):
            Validates and saves seller setup data.
            Returns a success response if setup is complete.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = SellerSetupSerializer(
            data=request.data,
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Seller setup complete"},
            status=status.HTTP_200_OK
        )



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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_resert'

    def post(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'message': 'Invalid data provided.',
                    'errors': serializer.errors
                },
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
                status=status.HTTP_200_OK
            )
        # Create the email context
        subject = "[Attention] Password Reset OTP"
        template_name = "reset_password_otp"
        recipient_list = [user.email]
        attachments = None  # No attachments needed for OTP resend
        context = {
            'otp_code': user.generate_otp()
        }
        # Send the email with OTP
        send_email_task.delay(
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
    summary="Verify Password Reset Request",
    description="Verifies a password reset request using an OTP code sent to the user's email.",
    request=ResetPasswordrequestVerifySerializer,
    responses={
        200: OpenApiResponse(
            description="Password reset request verified successfully. Returns JWT tokens and user info."
        ),
        400: OpenApiResponse(
            description="Invalid data, missing fields, or invalid OTP code."
        ),
        404: OpenApiResponse(
            description="User not found for the provided email."
        ),
    },
    examples=[
        OpenApiExample(
            name="Verify Password Reset Request",
            value={
                "email": "exmple@test.com",
                "otp": "123456"
            },
            request_only=True
        ),
        OpenApiExample(
            name="Successful Verification Response",
            value={
                "message": "Login successful.",
                "access_token": "eyJ0eXAiOiJKV1QiLCJh...",
                "user": {
                    "id": "1234",
                    "email": "exmple@test.com",
                }
            },
            response_only=True
        ),
    ]
   
)
class ResetPasswordrequestVerifyView(APIView):
    """
    APIView for verifying a password reset request using an OTP code.
    This view handles POST requests to verify a user's password reset request by validating
    the provided email and OTP code. If the credentials are valid, it generates JWT access
    and refresh tokens, sets the refresh token as an HTTP-only cookie, and returns the access
    token along with basic user information.
    Methods:
        post(request):
            Validates the provided email and OTP code. If valid, authenticates the user and
            returns JWT tokens. Handles error responses for invalid data, missing fields,
            non-existent users, and invalid OTP codes.
    Permissions:
        - AllowAny: No authentication required.
    Throttling:
        - AnonRateThrottle: Applies rate limiting to anonymous requests.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]


    def post(self, request):
        serializer = ResetPasswordrequestVerifySerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Invalid data for password reset verification: {serializer.errors}")
            return Response(
                {
                    'message': 'Invalid data provided.',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Extract email and OTP code from the validated data
        user_email = serializer.validated_data.get('email').strip().lower()
        otp_code = serializer.validated_data.get('otp').strip()
        if not user_email or not otp_code:
            logger.error(f"Missing email or OTP in request: {request.data}")
            return Response(
                {
                    'message': 'Email and OTP code are required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the user by email
        user = User.objects.filter(email=user_email).first()
        if not user:
            logger.warning("No user found with this email.")
            return Response(
                {
                    'message': f'User for email: "{user_email}" not found.'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.verify_otp(otp_code):
            logger.warning(f"Invalid OTP for user {user_email}")
            return Response(
                {
                    'message': 'Invalid OTP code.'
                },
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


@extend_schema(
    summary="Update User Password",
    description="Allows users to securely update their password by providing their registered email and a new password.",
    request=RequestUpdatePasswordSerializer,
    responses={
        200: OpenApiResponse(description="Password updated successfully. A confirmation email has been sent."),
        400: OpenApiResponse(description="Invalid input data or missing required fields."),
        404: OpenApiResponse(description="Email is not registered or does not exist."),
    },
    examples=[
        OpenApiExample(
            name="Update Password Request",
            value={
                "email": "example@teat.com",
                "password": "new_secure_password"
            },
            request_only=True
        ),
        OpenApiExample(
            name="Successful Update Response",
            value={
                "message": "Password updated successfully. A confirmation email has been sent."
            },
            response_only=True
        )
    ]
)
class RequestUpdatePasswordView(APIView):
    """
    APIView for handling password update requests.
    This view allows users to securely update their password by providing their registered email and a new password.
    It performs the following steps:
    - Validates the input data using `RequestUpdatePasswordSerializer`.
    - Checks if the provided email exists in the system.
    - Updates the user's password securely using Django's `set_password` method.
    - Sends a confirmation email asynchronously to the user upon successful password update.
    - Implements rate limiting using `ScopedRateThrottle` with the scope 'password_reset'.
    Responses:
    - 200 OK: Password updated successfully and confirmation email sent.
    - 400 Bad Request: Invalid input data or missing required fields.
    - 404 Not Found: Email is not registered or does not exist.
    Attributes:
        throttle_classes (list): List of throttle classes applied to this view.
        throttle_scope (str): Scope name for rate throttling.
    Methods:
        post(request): Handles POST requests to update the user's password.
    """
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_resert'
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = RequestUpdatePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'message': 'Invalid data provided.',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        email = serializer.validated_data['email'].strip().lower()
        if not email:
            logger.error("No email provided for password update request.")
            return Response(
                {
                    'message': 'Email is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"User with email {email} does not exist.")
            return Response(
                {
                    'message': 'Email is not registered or does not exist.'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        # Set the new password securely
        new_password = serializer.validated_data['new_password']
        if not new_password:
            logger.error("No new password provided for password update.")
            return Response(
                {
                    'message': 'New password is required.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # Update the user's password
        user.set_password(new_password)
        user.save()
    
        # Create the email context
        subject = "[Attention] Password Update"
        template_name = "update_password"
        recipient_list = [user.email]
        attachments = None  # No attachments needed for OTP
        now = timezone.now()
        formated_time_now = now.strftime("%Y-%m-%d %H:%M:%S")  # Get current time in a readable format
        context = {
            'user': user.first_name,
            'time_now': formated_time_now,
        }

        # Send Notification email
        # This task is asynchronous and will run in the background
        # It allows the user to continue using the application without waiting for the email to be sent
        send_email_task.delay(
            subject=subject,
            template_name=template_name,
            context=context,
            recipient_list=recipient_list,
            attachments=attachments
        )

        logger.info(f"Password updated successfully for user {email}.")
        return Response(
            {
                'message': 'Password updated successfully. A confirmation email has been sent.',
            },
            status=status.HTTP_200_OK
        )

@extend_schema(
    summary="Activate User Account",
    description="Activates a user account using a JWT token provided in the request body.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "JWT activation token"
                }
            },
            "required": ["token"]
        }
    },
    responses={
        200: OpenApiResponse(
            description="Account activated successfully. Returns user details.",
            examples=[
                OpenApiExample(
                    name="Successful Activation",
                    value={
                        "message": "Account activated successfully.",
                        "user": {
                            "id": "1234",
                            "email": "user@example.com",
                            "first_name": "John",
                            "last_name": "Doe",
                            "is_store_owner": True,
                            "is_verified": True,
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    },
                    response_only=True
                )
            ]
        ),
        400: OpenApiResponse(
            description="Invalid or expired token.",
            examples=[
                OpenApiExample(
                    name="Invalid Token",
                    value={
                        "message": "Invalid or expired token.",
                        "error": "Token is invalid or expired."
                    },
                    response_only=True
                )
            ]
        )
    }
)
class ActivateAccountView(APIView):
    """
    APIView for activating a user account using a JWT token.
    POST:
        Expects a JSON payload with a "token" field containing the activation JWT.
        - If the token is missing, returns HTTP 400 with an error message.
        - If the token is valid and the user is found:
            - Activates the user account if not already active.
            - Returns HTTP 200 with a success message and user details.
        - If the token is invalid or expired, returns HTTP 400 with an error message.
    Logging:
        - Logs errors for missing or invalid tokens.
        - Logs successful account activations.
    Permissions:
        - AllowAny: No authentication required to access this endpoint.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            logger.error("Activation token is required.")
            return Response(
                {
                    "message": "Token is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            access_token = AccessToken(token)
            user_id = access_token["user_id"]
            user = User.objects.get(id=user_id)
            if not user.is_active:
                user.is_active = True
                user.save()
                logger.info(f"User {user.email} activated successfully.")
            
            logger.info(f"Account activated for user {user.email}.")
            return Response(
                {
                    "message": "Account activated successfully.",
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_store_owner": user.is_store_owner,
                        "is_verified": user.is_active,
                        "created_at": user.created_at.isoformat()
                    },
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Failed to activate account: {e}", exc_info=True)
            return Response(
                {
                    "message": "Invalid or expired token.",
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
