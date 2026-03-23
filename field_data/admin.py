from django.contrib import admin
from .models import (
    ExcelUpload,
    HybridDistribution,
    MonthlyHarvest,
    NurseryOperation,
    PollenProduction,
    NurseryBatch,
    NurseryBatchVariety,
)


@admin.register(ExcelUpload)
class ExcelUploadAdmin(admin.ModelAdmin):
    list_display = ('upload_type', 'uploaded_by', 'records_created', 'created_at')
    list_filter = ('upload_type',)


@admin.register(HybridDistribution)
class HybridDistributionAdmin(admin.ModelAdmin):
    list_display = ('municipality', 'barangay', 'farmer_last_name', 'variety', 'seedlings_received', 'date_received', 'field_site')
    list_filter = ('field_site', 'variety', 'report_month')
    search_fields = ('farmer_last_name', 'farmer_first_name', 'municipality', 'barangay')


@admin.register(MonthlyHarvest)
class MonthlyHarvestAdmin(admin.ModelAdmin):
    list_display = ('location', 'farm_name', 'area_ha', 'num_hybridized_palms', 'variety', 'field_site')
    list_filter = ('field_site', 'report_month')
    search_fields = ('location', 'farm_name')


class NurseryBatchVarietyInline(admin.TabularInline):
    model = NurseryBatchVariety
    extra = 1


class NurseryBatchInline(admin.TabularInline):
    model = NurseryBatch
    extra = 1
    show_change_link = True


@admin.register(NurseryBatch)
class NurseryBatchAdmin(admin.ModelAdmin):
    list_display = ('nursery', 'seednuts_harvested', 'date_harvested', 'source_of_seednuts')
    inlines = [NurseryBatchVarietyInline]


@admin.register(NurseryOperation)
class NurseryOperationAdmin(admin.ModelAdmin):
    list_display = ('proponent_entity', 'proponent_representative', 'target_seednuts', 'report_type', 'field_site')
    list_filter = ('field_site', 'report_type', 'report_month')
    search_fields = ('proponent_entity', 'proponent_representative')
    inlines = [NurseryBatchInline]


@admin.register(PollenProduction)
class PollenProductionAdmin(admin.ModelAdmin):
    list_display = ('month_label', 'ending_balance_prev', 'total_utilization', 'ending_balance', 'field_site')
    list_filter = ('field_site', 'report_month')

