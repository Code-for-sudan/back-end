from django.db import models
from django.conf import settings
from django.utils import timezone

class VerificationCode(models.Model):
    """
    Model to store verification codes for user authentication
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name='verification_codes'
    )
    code = models.CharField(max_length=6)
    code_type = models.CharField(
        max_length=20,
        choices=[
            ('phone', 'Phone Verification'),
            ('email', 'Email Verification'),
            ('password_reset', 'Password Reset'),
        ]
    )
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Set expiration to 15 minutes from now
            self.expires_at = timezone.now() + timezone.timedelta(minutes=15)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def is_valid(self):
        return not self.is_used and not self.is_expired()
    
    def mark_as_used(self):
        """Mark the verification code as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    def __str__(self):
        return f"Code for {self.user.email} - {self.code_type}"
