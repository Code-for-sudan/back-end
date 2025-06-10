import requests, logging
from rest_framework import status # type: ignore
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, throttle_classes # type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from .serializers import LoginSerializer, ResetPasswordConfirmSerializer
from accounts.serializers import UserSerializer
from .utils import generate_jwt_tokens
from accounts.tasks import send_email_task


# Create a logger for this module
logger = logging.getLogger('authentication_views')

# Get the user model
User = get_user_model()

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

class ResetPasswordVerifyView(APIView):
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
            logger.warning(f"User with email {user_email} not found.")
            return Response(
                {'message': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
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

class ResetPasswordConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        """
        Handles password reset by verifying OTP, validating new password, and setting the new password.
        Args:
            request (Request): The HTTP request object containing email, OTP, and new password.
        Returns:
            Response:
                - 200 OK with a success message if OTP is valid and password is reset.
                - 400 BAD REQUEST with an error message if any field is missing, the user does not exist, or OTP is invalid.
        Raises:
            KeyError: If 'email', 'otp', or 'new_password' is not present in the request data.
        Side Effects:
            - Logs errors for missing fields, invalid OTP, invalid password, or non-existent users.
            - Updates the user's password if OTP verification and password validation are successful.
        """
        try:
            email = request.data.get('email')
            otp = request.data.get('otp')
            new_password = request.data.get('new_password')
        except KeyError:
            logger.error('Email, OTP, and new password are required.')
            return Response({'message': 'Email, OTP, and new password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Password reset attempt for email: {email}")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.error(f"User with email {email} does not exist.")
            return Response({'message': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.verify_otp(otp):
            logger.error(f"Invalid or expired OTP for user {email}.")
            return Response({'message': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ResetPasswordConfirmSerializer()
        try:
            serializer.validate_new_password(new_password)
        except Exception as e:
            logger.error(f"Password validation failed for user {email}: {e}")
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        logger.info(f"Password reset successful for user {email}.")
        return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)

class ResetPasswordRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        """
        Handles resending OTP to a user's email.
        Args:
            request (Request): The HTTP request object containing the user's email.
        Returns:
            Response: 200 OK if OTP is resent, 400 BAD REQUEST if email is missing or user does not exist.
        Side Effects:
            - Generates and sends a new OTP via email.
            - Logs all actions and errors.
        """
        email = request.data.get('email', '').strip().lower()
        if not email:
            logger.error("No email provided for OTP resend.")
            return Response({'message': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.error(f"User with email {email} does not exist for OTP resend.")
            return Response({'message': 'User with this email does not exist.'}, status=status.HTTP_400_BAD_REQUEST)

        otp = user.generate_otp()
        subject = "Your OTP Code"
        body = f"Your OTP code is: {otp}"

        # Send OTP via email using Celery task
        send_email_task.delay([email], subject, body)

        logger.info(f"OTP resent to user {email}.")
        return Response({'message': 'OTP has been resent to your email.'}, status=status.HTTP_200_OK)