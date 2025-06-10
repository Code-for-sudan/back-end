
import logging
from rest_framework.views import APIView
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated # type: ignore
from drf_spectacular.utils import extend_schema
from .serializers import UserSerializer, BusinessOwnerSignupSerializer # type: ignore
from rest_framework import status # type: ignore
from .models import User # type: ignore


# Create a logger for this module
logger = logging.getLogger('accounts_views')


class SignupUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Handles user registration.
        This view function receives a request containing user data, validates it using the UserSerializer,
        and creates a new user if the email does not already exist in the database. If the email is already
        registered, it returns a 400 Bad Request response. On successful creation, it returns a 201 Created
        response with the user data. If validation fails, it returns a 400 Bad Request response with error details.
        Args:
            request (Request): The HTTP request object containing user registration data.
        Returns:
            Response: A DRF Response object with a message and status code indicating the result of the operation.
        """
        serializer = UserSerializer(data=request.data)
        if User.objects.filter(email=request.data.get('email')).exists():
            # Log the error message
            logger.error('User already exists.')
            return Response(
                {'message': 'User already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'User created successfully.',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        else:
            # Log the error message
            logger.error('User creation failed: {}.'.format(serializer.errors))
            return Response(
                {
                    'message': 'User creation failed.',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class SignupBusinessOwnerView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Handles business owner registration.
        This view function receives a request containing business owner data, validates it using the BusinessOwner serializer,
        and creates a new business owner if the email does not already exist in the database. If the email is already
        registered, it returns a 400 Bad Request response. On successful creation, it returns a 201 Created
        response with the business owner data. If validation fails, it returns a 400 Bad Request response with error details.
        Args:
            request (Request): The HTTP request object containing business owner registration data.
        Returns:
            Response: A DRF Response object with a message and status code indicating the result of the operation.
        """
        serializer = BusinessOwnerSignupSerializer(data=request.data)
        if User.objects.filter(email=request.data.get('email')).exists():
            # Log the error message
            logger.error('Business owner already exists.')
            return Response(
                {'message': 'Business owner already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Business owner created successfully.',
                    'data': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        else:
            # Log the error message
            logger.error('Business owner creation failed: {}.'.format(serializer.errors))
            return Response(
                {
                    'message': 'Business owner creation failed.',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )