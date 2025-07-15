import os
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError # type: ignore
from ..serializers import UserSerializer, BusinessOwnerSignupSerializer
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError
from rest_framework import status
from django.urls import reverse
from django.test import TestCase
from ..models import User, BusinessOwner
from rest_framework.test import APITestCase

class UserSerializerTest(TestCase):
    """
    Test suite for the UserSerializer.
    This test suite includes the following test cases:
    - test_valid_user_serializer: Tests that a serializer with valid user data is valid.
    - test_invalid_user_serializer_missing_fields: Tests that a serializer with missing required fields is invalid and raises appropriate errors.
    - test_invalid_user_serializer_short_password: Tests that a serializer with a password that is too short is invalid and raises appropriate errors.
    - test_validate_profile_picture_valid_image: Tests that a serializer with a valid profile picture image is valid.
    - test_validate_profile_picture_invalid_extension: Tests that a serializer with an invalid profile picture image extension raises a ValidationError.
    - test_validate_profile_picture_large_image: Tests that a serializer with a profile picture image that is too large raises a ValidationError.
    - test_create_user: Tests that a user can be successfully created with valid data and that the created user's attributes match the input data.
    """

    def setUp(self):
        self.valid_user_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'password123',
            'gender': 'M'
        }

    def test_valid_user_serializer(self):
        serializer = UserSerializer(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], self.valid_user_data['email'])

    def test_account_type_field(self):
        user = User.objects.create_user(**self.valid_user_data, is_store_owner=True)
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data['account_type'], 'seller')
        user.is_store_owner = False
        user.save()
        serializer = UserSerializer(user)
        self.assertEqual(serializer.data['account_type'], 'buyer')

    def test_invalid_user_serializer_missing_fields(self):
        invalid_data = self.valid_user_data.copy()
        invalid_data.pop('email')
        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_invalid_user_serializer_short_password(self):
        invalid_data = self.valid_user_data.copy()
        invalid_data['password'] = '123'
        serializer = UserSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_validate_profile_picture_valid_image(self):
        image_path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.png')
        with open(image_path, 'rb') as image_file:
            image = SimpleUploadedFile('test_1.png', image_file.read(), content_type='image/png')
            data = self.valid_user_data.copy()
            data['profile_picture'] = image
            serializer = UserSerializer(data=data)
            self.assertTrue(serializer.is_valid())

    def test_validate_profile_picture_invalid_extension(self):
        image_path = os.path.join(os.path.dirname(__file__), 'media', 'test_2.webp')
        with open(image_path, 'rb') as image_file:
            image = SimpleUploadedFile('test_2.webp', image_file.read(), content_type='image/webp')
            data = self.valid_user_data.copy()
            data['profile_picture'] = image
            serializer = UserSerializer(data=data)
            with self.assertRaises(ValidationError):
                serializer.is_valid(raise_exception=True)

    def test_validate_profile_picture_large_image(self):
        image_path = os.path.join(os.path.dirname(__file__), 'media', 'test_3.jpg')
        with open(image_path, 'rb') as image_file:
            image = SimpleUploadedFile('test_3.jpg', image_file.read(), content_type='image/jpg')
            data = self.valid_user_data.copy()
            data['profile_picture'] = image
            serializer = UserSerializer(data=data)
            with self.assertRaises(ValidationError):
                serializer.is_valid(raise_exception=True)

class BusinessOwnerSignupTests(APITestCase):
    """
    Test suite for business owner signup functionality.
    """

    def setUp(self):
        self.user_data = {
            'email': 'owner@example.com',
            'first_name': 'Owner',
            'last_name': 'Test',
            'password': 'ownerpass123',
            'gender': 'F'
        }
        self.data = {
            'email': 'owner@example.com',
            'first_name': 'Owner',
            'last_name': 'Test',
            'password': 'ownerpass123',
            'gender': 'F',
            'store_name': 'My Store',
            'store_location': 'Khartoum',
            'description': 'Best store',
            'store_type': 'Retail'
        }

    def test_business_owner_signup_serializer_valid(self):
        serializer = BusinessOwnerSignupSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())
        business_owner = serializer.save()
        self.assertIsInstance(business_owner, BusinessOwner)
        self.assertEqual(business_owner.user.email, self.user_data['email'])
        self.assertEqual(business_owner.user.account_type, 'seller')
        self.assertTrue(business_owner.user.is_store_owner)
        self.assertEqual(business_owner.store.name, self.data['store_name'])

    def test_account_type_field(self):
        serializer = BusinessOwnerSignupSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())
        business_owner = serializer.save()
        self.assertEqual(serializer.data['account_type'], 'seller')

    def test_missing_required_fields(self):
        invalid_data = self.data.copy()
        invalid_data.pop('store_name')
        serializer = BusinessOwnerSignupSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('store_name', serializer.errors)
