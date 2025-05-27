from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializer

class LoginView(APIView):
    '''
    An API view for user login that handles authentication and returns JWT tokens.
    '''
    def post(self, request):
        serializer = LoginSerializer(data=request.data) # Initialize the serializer with request data
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user) # Create JWT tokens
            user_data = {
                "id": user.id,
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}".strip(), # name is a combination of first and last name
            }
            return Response({
                # if login is successful, return the tokens and user data
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) # If validation fails, return errors with 400 status
