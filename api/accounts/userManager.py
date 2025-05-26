""" User Manager for handling user creation and management in Django. """
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        """
        Creates and saves a new user with the given email and password.
        Args:
            email (str): The email address of the user.
            password (str): The password for the user.
            **extra_fields: Additional fields to include in the user model.
        Raises:
            ValueError: If the email or password is not provided.
        Returns:
            user: The created user instance.
        """
        
        # Check for email and password
        if not email or not password:
            raise ValueError("User must have un email address and password")

        # Convetr to lowercase
        email = self.normalize_email(email=email)
        # Refers to the model that this manager is attached to
        user = self.model(email=email, **extra_fields)
        # Hash password
        user.set_password(password)
        # Save the  user instance to database
        user.save(using=self.db)

        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and return a superuser with the given email and password.
        This method sets the necessary fields to grant the user superuser privileges.
        Args:
            email (str): The email address of the superuser.
            password (str): The password for the superuser.
            **extra_fields: Additional fields to set for the superuser.
        Returns:
            User: The created superuser instance.
        """
        
        # It just set the admin privileges by adding the fields to the normal user.
        extra_fields.setdefault("is_staff", True)  # Superuser must be staff
        extra_fields.setdefault("is_superuser", True)  # Superuser must have superuser privileges

        return self.create_user(email, password, **extra_fields)
