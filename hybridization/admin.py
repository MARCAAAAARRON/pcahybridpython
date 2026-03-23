from django.contrib import admin
from .models import HybridizationRecord, RecordImage


class RecordImageInline(admin.TabularInline):
    model = RecordImage
    extra = 0


@admin.register(HybridizationRecord)
class HybridizationRecordAdmin(admin.ModelAdmin):
    list_display = ('hybrid_code', 'crop_type', 'field_site', 'status', 'created_by', 'updated_at')
    list_filter = ('status', 'field_site', 'growth_status')
    search_fields = ('hybrid_code', 'crop_type')
    inlines = [RecordImageInline]
