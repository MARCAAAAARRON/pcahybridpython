from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class FieldSite(models.Model):
    """Represents a PCA field site (e.g., Loay Farm, Balilihan Farm)."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Dynamic Signatories
    prepared_by_label = models.CharField(max_length=50, default='Prepared by:', blank=True)
    prepared_by_name = models.CharField(max_length=100, blank=True)
    prepared_by_title = models.CharField(max_length=100, blank=True)

    reviewed_by_label = models.CharField(max_length=50, default='Reviewed by:', blank=True)
    reviewed_by_name = models.CharField(max_length=100, blank=True)
    reviewed_by_title = models.CharField(max_length=100, blank=True)

    noted_by_label = models.CharField(max_length=50, default='Noted by:', blank=True)
    noted_by_name = models.CharField(max_length=100, blank=True)
    noted_by_title = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class UserProfile(models.Model):
    """Extends Django User with role and field site assignment."""
    ROLE_CHOICES = [
        ('supervisor', 'COS / Agriculturist'),
        ('admin', 'Senior Agriculturist'),
        ('superadmin', 'PCDM / Division Chief I'),
        ('sysadmin', 'System Administrator'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='supervisor')
    field_site = models.ForeignKey(
        FieldSite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Assigned field site (for supervisors only)'
    )
    middle_initial = models.CharField(max_length=10, blank=True)
    signature_image = models.ImageField(upload_to='signatures/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    class Meta:
        ordering = ['user__username']


class Notification(models.Model):
    """In-app notification for users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=500)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'[Read]' if self.is_read else '[Unread]'} {self.message[:50]}"

    class Meta:
        ordering = ['-created_at']


# Removed auto-create signals as they conflict with Django Admin InlineModelAdmin
# Profile creation and updates should be handled by forms and admin classes explicitly.
