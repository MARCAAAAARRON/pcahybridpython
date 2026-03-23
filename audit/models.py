from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    """Records all significant system events for audit trail."""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('submit', 'Submit'),
        ('validate', 'Validate'),
        ('revision', 'Request Revision'),
        ('report', 'Generate Report'),
        ('user_mgmt', 'User Management'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def get_formatted_details(self):
        if not self.details:
            return "—"
        try:
            items = []
            for k, v in self.details.items():
                if k == 'type' or not v:
                    continue  # skip redundant type label or empty values
                clean_key = k.replace('_', ' ').title()
                items.append(f"{clean_key}: {v}")
            
            if not items:
                # If there was only a 'type' key or everything was empty, return standard label
                return self.details.get('type', '—')
                
            return " | ".join(items)
        except Exception:
            return str(self.details)

    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {self.user} — {self.get_action_display()}"

    class Meta:
        ordering = ['-timestamp']
