import logging
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer


logger = logging.getLogger('authentication_views') # Create Logger

class LoginView(APIView):
    '''
    An API view for user login that handles authentication and returns JWT tokens.
    '''
    serializer_class = LoginSerializer  # Added to be detected for documentation

    def post(self, request):
        serializer = self.serializer_class(data=request.data) # Initialize the serializer with request data
        if serializer.is_valid():
            user = serializer.validated_data['user']
            logger.info(f"Login successful for user id: {user.id}")
            refresh = RefreshToken.for_user(user) # Create JWT tokens
            user_data = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name, # Temporary, changed later to match the expected output
            }
            return Response({
                # if login is successful, return the tokens and user data
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data
            })
        # Check if there are any non-field errors in the serializer's validation errors.
        # If "non_field_errors" is present or contains the specific message "Invalid email or password.",
        # return a 401 Unauthorized response with the serializer's errors.
        # Otherwise, return a 400 Bad Request response with the serializer's errors.
        if "non_field_errors" in serializer.errors or "Invalid email or password." in serializer.errors.get("non_field_errors", []):
            logger.warning(f"Login failed for email: {request.data.get('email')}. Reason: Invalid credentials.")
            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
        logger.error(f"Login failed for email: {request.data.get('email')}. Errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
