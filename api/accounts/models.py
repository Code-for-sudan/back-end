import os, random, hashlib, logging, secrets
from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, Group, Permission
from django.utils.timezone import now
from accounts.userManager import UserManager
from stores.models import Store
from phonenumber_field.modelfields import PhoneNumberField

# Create a models
logger = logging.getLogger('accounts_models')

class User(AbstractBaseUser, PermissionsMixin):
    """"
    User Model
    This model represents a user in the system and extends Django's AbstractBaseUser and PermissionsMixin classes.
    It includes fields for user information, such as email, first name, last name, profile picture, OTP (One-Time Password),
    and gender. The model also includes methods for generating and verifying OTPs.
    Attributes:
        MALE (str): Constant for male gender.
        FEMALE (str): Constant for female gender.
        GENDER_CHOICES (list): List of tuples representing gender choices.
        email (EmailField): User's email address, used as the unique identifier.
        first_name (CharField): User's first name, default is "Unknown".
        last_name (CharField): User's last name, default is "Unknown".
        profile_picture (ImageField): User's profile picture, optional.
        otp (CharField): Hashed OTP for user verification, optional.
        otp_expires_at (DateTimeField): Expiration time for the OTP, optional.
        is_active (BooleanField): Indicates whether the user is active.
        is_staff (BooleanField): Indicates whether the user has admin access.
        created_at (DateTimeField): Timestamp when the user was created.
        updated_at (DateTimeField): Timestamp when the user was last updated.
        account_type (CharField): Type of account, either 'seller' or 'buyer'.
        phone_number (PhoneNumberField): User's phone number, optional and unique.
        whatsapp_number PhoneNumberField): User's phone number, optional and unique.
        gender (CharField): User's gender, with choices defined in GENDER_CHOICES.
        groups (ManyToManyField): Groups the user belongs to.
        user_permissions (ManyToManyField): Permissions assigned to the user.
        objects (UserManager): Manager for the User model.
        USERNAME_FIELD (str): Field used as the unique identifier for authentication.
        REQUIRED_FIELDS (list): List of required fields when creating a superuser.
    Methods:
        generate_otp(): Generates a 6-digit OTP, hashes it, and saves it to the model instance.
        verify_otp(otp_input): Verifies the provided OTP against the stored OTP.
        __str__(): Returns a string representation of the user.
    """
    # Desfine the general fields
    MALE = 'M'
    FEMALE = 'F'
    # Note that the gender in the request is ("M" or "F")
    GENDER_CHOICES = [
        (MALE, 'Male'),
        (FEMALE, 'Female'),
    ]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    email = models.EmailField(unique=True)  # Use email instead of username
    first_name = models.CharField(max_length=50, default="Unknown")
    last_name = models.CharField(max_length=50, default="Unknown")
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    phone_number = PhoneNumberField(blank=True, null=True, unique=True, db_index=True)
    whatsapp_number = PhoneNumberField(blank=True, null=True, unique=True, db_index=True)
    otp = models.CharField(max_length=64, blank=True, null=True, db_index=True)  # Store hashed OTP
    otp_expires_at = models.DateTimeField(blank=True, null=True, db_index=True)  # Expiration time
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  # Required for admin access
    is_store_owner = models.BooleanField(default=False)  # Indicates if the user is a store owner
    s_subscribed = models.BooleanField(default=False, help_text="Is the user subscribed to the newsletter?")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    account_type = models.CharField(
        max_length=10,
        choices=[('seller', 'Seller'), ('buyer', 'Buyer')],
        default='buyer',
        help_text="Type of account: 'seller' or 'buyer'."
    )
    gender = models.CharField( # Only one option can be selected here
        max_length=1,
        choices=GENDER_CHOICES,
        null=True  # Default value (optional), coz men are awesome
    )
    location = models.CharField(max_length=255, blank=True, null=True)  # Optional location field
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total amount spent by the user in the store."
    )
    # No password field is not explicitly defined
    # because it is inherited from Django's AbstractBaseUser class,
    # which provides the password field and related methods
    # for handling passwords securely.

    # Set the user groups and permissions for the user model
    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    # Set the user manager model
    objects = UserManager()
    # Those line for the create superuser command 
    USERNAME_FIELD = 'email'  # Set email as the unique identifier
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Required when creating superusers

    @property
    def last_cart(self):
        return self.carts.first()

    def generate_otp(self):
        """
        Generates a One-Time Password (OTP), hashes it for security, and saves it to the model instance.
        The OTP is a 6-digit number that expires in 5 minutes. The hashed OTP and its expiration time
        are saved to the model instance, and the plain OTP is returned for sending via email or SMS.
        Returns:
            str: The plain 6-digit OTP.
        """

        otp_code = str(secrets.randbelow(900000) + 100000)  # 6-digit OTP
        hashed_otp = hashlib.sha256(otp_code.encode()).hexdigest()  # Hash OTP for security
        self.otp = hashed_otp
        self.otp_expires_at = now() + timedelta(minutes=5)  # OTP expires in 5 minutes
        self.save()
        return otp_code  # Return plain OTP for sending via email/SMS

    def verify_otp(self, otp_input):
        """
        Verify the provided OTP (One-Time Password) against the stored OTP.
        Args:
            otp_input (str): The OTP input provided by the user.
        Returns:
            bool: True if the OTP is verified successfully, False otherwise.
        Logs:
            - "OTP input is empty." if the provided OTP input is empty.
            - "OTP has expired." if the OTP has expired.
            - "Invalid OTP." if the provided OTP does not match the stored OTP.
            - "OTP verified successfully." if the OTP is verified successfully.
        Side Effects:
            - Clears the stored OTP and its expiration time upon successful verification.
            - Saves the changes to the database.
        """

        if not otp_input:
            logger.info("OTP input is empty.")
            return False
        
        # Chech the opt code time
        if not self.otp_expires_at or now() > self.otp_expires_at:
            logger.info("OTP has expired.")
            return False

        hashed_input_otp = hashlib.sha256(otp_input.encode()).hexdigest()
        if self.otp != hashed_input_otp:
            logger.info("Invalid OTP.")
            return False

        self.otp = None  # Clear OTP after successful verification
        self.otp_expires_at = None
        self.save()
        logger.info("OTP verified successfully.")
        return True

    def __str__(self):
        return f"Email: {self.email}, First Name: {self.first_name}, Last Name: {self.last_name}, Gender: {self.gender}"


class BusinessOwner(models.Model):
    """
    Represents a business owner profile that extends the User model.
    This model creates a one-to-one relationship between a User and a Store,
    allowing each user to have a unique business owner profile associated with a specific store.
    Attributes:
        user (OneToOneField): Reference to the User associated with this business owner profile.
        store (OneToOneField): Reference to the Store owned by this business owner.
    Methods:
        __str__(): Returns a string representation of the business owner, displaying the user's first name and email.
    """

    # Extend the user model to create a business owner profile
    # TODO: Add more fields to the business owner profile
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business_owner_profile')
    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='owner')

    def __str__(self):
        return f"{self.user.first_name} ({self.user.email})"


class Cart(models.Model):
    """
    Represents a shopping cart associated with a user.
    Fields:
        user (ForeignKey): Reference to the User who owns the cart.
        status (CharField): The current status of the cart. Choices are 'active', 'abandoned', or 'completed'.
        total_spent (FloatField): The total amount spent in this cart.
        last_purchase_date (DateTimeField): The date and time of the last purchase made with this cart.
        created_at (DateTimeField): Timestamp when the cart was created.
        updated_at (DateTimeField): Timestamp when the cart was last updated.
    Meta:
        ordering: Carts are ordered by creation date in descending order.
    """

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('abandoned', 'Abandoned'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='carts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_spent = models.FloatField(default=0.0)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
