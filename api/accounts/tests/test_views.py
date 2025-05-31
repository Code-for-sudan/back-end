import os
from django.urls import reverse
from rest_framework.test import APITestCase # type: ignore
from rest_framework import status # type: ignore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore
from ..models import User

User = get_user_model()

class UserSignupTests(APITestCase):
    """
    Test suite for user signup functionality.
    Classes:
        UserSignupTests: Test cases for user signup API endpoint.
    Methods:
        setUp(self):
            Sets up the test environment by defining the signup URL and user data.
        test_signup_success(self):
            Tests that a user can successfully sign up with valid data.
        test_signup_user_already_exists(self):
            Tests that attempting to sign up with an email that already exists returns a 400 status code.
        test_signup_invalid_data(self):
            Tests that attempting to sign up with invalid data returns a 400 status code and appropriate error message.
    """

    def setUp(self):
        self.signup_url = reverse('signup')
        self.image_path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.png')
        with open(self.image_path, 'rb') as image_file:
            self.user_data = {
                'email': 'testuser@example.com',
                'password': 'testpassword123',
                'first_name': 'Test',
                'gender': 'M',
                'last_name': 'User',
                'profile_picture': SimpleUploadedFile(name='test_1.png', content=image_file.read(), content_type='image/png')
            }

    def test_signup_success(self):
        response = self.client.post(self.signup_url, self.user_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message'], 'User created successfully.')
        self.assertIn('data', response.data)

    def test_signup_user_already_exists(self):
        User.objects.create_user(**self.user_data)
        response = self.client.post(self.signup_url, self.user_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'User already exists.')

    def test_signup_invalid_data(self):
        invalid_data = self.user_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post(self.signup_url, invalid_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'User creation failed.')
        self.assertIn('errors', response.data)
