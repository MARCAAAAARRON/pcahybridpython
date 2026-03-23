from django.db import models
from django.contrib.auth.models import User
from accounts.models import FieldSite
from field_data.models import ApprovalTrackingModel


class HybridizationRecord(ApprovalTrackingModel):
    """Core hybridization data record."""
    GROWTH_STATUS_CHOICES = [
        ('seedling', 'Seedling'),
        ('vegetative', 'Vegetative'),
        ('flowering', 'Flowering'),
        ('fruiting', 'Fruiting'),
        ('harvested', 'Harvested'),
    ]

    field_site = models.ForeignKey(FieldSite, on_delete=models.CASCADE, related_name='records')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records')
    crop_type = models.CharField(max_length=100)
    parent_line_a = models.CharField(max_length=100, verbose_name='Parent Line A')
    parent_line_b = models.CharField(max_length=100, verbose_name='Parent Line B')
    hybrid_code = models.CharField(max_length=50, unique=True)
    date_planted = models.DateField()
    growth_status = models.CharField(max_length=20, choices=GROWTH_STATUS_CHOICES, default='seedling')
    notes = models.TextField(blank=True)
    admin_remarks = models.TextField(blank=True, help_text='Remarks from admin during validation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.hybrid_code} — {self.crop_type}"

    class Meta:
        ordering = ['-updated_at']


class RecordImage(models.Model):
    """Field images attached to a hybridization record."""
    record = models.ForeignKey(HybridizationRecord, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='hybridization_images/%Y/%m/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.record.hybrid_code}"
