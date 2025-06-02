import os
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError # type: ignore
from ..serializers import UserSerializer
from unittest import mock
from ..serializers import BusinessOwnerSignupSerializer
from ..models import BusinessOwner
from stores.models import Store


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

    def test_create_user(self):
        serializer = UserSerializer(data=self.valid_user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, self.valid_user_data['email'])
        self.assertEqual(user.first_name, self.valid_user_data['first_name'])
        self.assertEqual(user.last_name, self.valid_user_data['last_name'])
        self.assertTrue(user.check_password(self.valid_user_data['password']))
        self.assertEqual(user.gender, self.valid_user_data['gender'])


class BusinessOwnerSignupSerializerTest(TestCase):
    """
    Test suite for the BusinessOwnerSignupSerializer.
    """

    def setUp(self):
        self.valid_data = {
            'email': 'owner@example.com',
            'first_name': 'Alice',
            'last_name': 'Smith',
            'password': 'securepass',
            'gender': 'F',
            'store_name': 'Test Store'
        }

    def test_valid_business_owner_signup_serializer(self):
        serializer = BusinessOwnerSignupSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_missing_required_fields(self):
        data = self.valid_data.copy()
        data.pop('email')
        serializer = BusinessOwnerSignupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_short_password(self):
        data = self.valid_data.copy()
        data['password'] = '123'
        serializer = BusinessOwnerSignupSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_validate_profile_picture_valid_image(self):
        image_path = os.path.join(os.path.dirname(__file__), 'media', 'test_1.png')
        with open(image_path, 'rb') as image_file:
            image = SimpleUploadedFile('test_1.png', image_file.read(), content_type='image/png')
            data = self.valid_data.copy()
            data['profile_picture'] = image
            serializer = BusinessOwnerSignupSerializer(data=data)
            self.assertTrue(serializer.is_valid())

    def test_validate_profile_picture_invalid_extension(self):
        image_path = os.path.join(os.path.dirname(__file__), 'media', 'test_2.webp')
        with open(image_path, 'rb') as image_file:
            image = SimpleUploadedFile('test_2.webp', image_file.read(), content_type='image/webp')
            data = self.valid_data.copy()
            data['profile_picture'] = image
            serializer = BusinessOwnerSignupSerializer(data=data)
            with self.assertRaises(ValidationError):
                serializer.is_valid(raise_exception=True)

    def test_validate_profile_picture_large_image(self):
        image_path = os.path.join(os.path.dirname(__file__), 'media', 'test_3.jpg')
        with open(image_path, 'rb') as image_file:
            image = SimpleUploadedFile('test_3.jpg', image_file.read(), content_type='image/jpg')
            data = self.valid_data.copy()
            data['profile_picture'] = image
            serializer = BusinessOwnerSignupSerializer(data=data)
            with self.assertRaises(ValidationError):
                serializer.is_valid(raise_exception=True)

    @mock.patch('stores.models.Store.objects.create')
    @mock.patch('..models.BusinessOwner.objects.create_user')
    def test_create_business_owner_and_store(self, mock_create_user, mock_store_create):
        # Mock the Store and BusinessOwner creation
        mock_store = mock.Mock(spec=Store)
        mock_store_create.return_value = mock_store
        mock_owner = mock.Mock(spec=BusinessOwner)
        mock_create_user.return_value = mock_owner

        serializer = BusinessOwnerSignupSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        owner = serializer.save()
        mock_store_create.assert_called_once_with(name=self.valid_data['store_name'])
        mock_create_user.assert_called_once()
        self.assertEqual(owner, mock_owner)
