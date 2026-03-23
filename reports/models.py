from django.db import models
from django.contrib.auth.models import User
from accounts.models import FieldSite


class Report(models.Model):
    """Tracks generated reports (PDF/CSV)."""
    REPORT_TYPE_CHOICES = [
        ('pdf', 'PDF Report'),
        ('csv', 'CSV Export'),
        ('excel', 'Excel Export'),
    ]

    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_reports')
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    field_site = models.ForeignKey(
        FieldSite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Null = consolidated report'
    )
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='reports/%Y/%m/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"

    class Meta:
        ordering = ['-created_at']
