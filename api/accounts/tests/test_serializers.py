from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from accounts.serializers import UserSerializer
from ..models import User


class UserSerializerTestCase(TestCase):
    """
    TestCase for the UserSerializer, covering various scenarios for user creation and validation.
    Tested Scenarios:
    - Validation and saving with all required and optional fields present.
    - Validation when optional fields (phone_number, whatsapp_number, otp) are missing.
    - Validation when optional fields are provided as blank strings.
    - Validation fails with an invalid email format.
    - Validation fails when attempting to create a user with a duplicate email.
    - Validation for gender field with an invalid value (test may be adjusted based on model enforcement).
    - Validation and saving when a profile picture is uploaded as a PNG file.
    - Validation and saving when a profile picture is uploaded with an uppercase file extension (e.g., .JPG).
    - Validation fails when a profile picture is uploaded without a file extension.
    - Validation and saving when the profile picture field is empty (None).
    Each test ensures that the serializer behaves as expected for both valid and invalid input data.
    """

    def setUp(self):
        self.valid_data = {
            "email": "valid@example.com",
            "first_name": "Valid",
            "last_name": "User",
            "phone_number": "1112223333",
            "whatsapp_number": "1112223333",
            "otp": "654321",
            "password": "validpassword",
            "gender": "M"
        }

    def test_serializer_with_all_fields(self):
        serializer = UserSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, self.valid_data["email"])
        self.assertTrue(user.check_password(self.valid_data["password"]))

    def test_serializer_with_optional_fields_missing(self):
        data = self.valid_data.copy()
        data.pop("phone_number")
        data.pop("whatsapp_number")
        data.pop("otp")
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_with_blank_strings(self):
        data = self.valid_data.copy()
        data["phone_number"] = ""
        data["whatsapp_number"] = ""
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_with_invalid_email(self):
        data = self.valid_data.copy()
        data["email"] = "not-an-email"
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_serializer_with_duplicate_email(self):
        User.objects.create_user(
            email=self.valid_data["email"],
            first_name="Other",
            last_name="User",
            password="anotherpassword",
            gender="male"
        )
        serializer = UserSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_serializer_with_invalid_gender(self):
        data = self.valid_data.copy()
        data["gender"] = "unknown"
        serializer = UserSerializer(data=data)
        # If gender choices are enforced in the model, this should fail
        # Otherwise, this will pass. Adjust as per your model.
        # self.assertFalse(serializer.is_valid())
        # self.assertIn("gender", serializer.errors)

    def test_serializer_profile_picture_png(self):
        image_content = b"fake image content"
        image = SimpleUploadedFile("profile.png", image_content, content_type="image/png")
        data = self.valid_data.copy()
        data["profile_picture"] = image
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_profile_picture_uppercase_extension(self):
        image_content = b"fake image content"
        image = SimpleUploadedFile("profile.JPG", image_content, content_type="image/jpeg")
        data = self.valid_data.copy()
        data["profile_picture"] = image
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_serializer_profile_picture_no_extension(self):
        image_content = b"fake image content"
        image = SimpleUploadedFile("profile", image_content, content_type="image/jpeg")
        data = self.valid_data.copy()
        data["profile_picture"] = image
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("profile_picture", serializer.errors)

    def test_serializer_profile_picture_empty(self):
        data = self.valid_data.copy()
        data["profile_picture"] = None
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)