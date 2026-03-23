from django.db import models
from django.contrib.auth.models import User
from accounts.models import FieldSite


class ExcelUpload(models.Model):
    """Tracks each Excel file upload."""
    UPLOAD_TYPE_CHOICES = [
        ('distribution', 'Hybrid Distribution'),
        ('harvest', 'Monthly Harvest'),
        ('nursery', 'Nursery Operations'),
        ('pollen', 'Pollen Production'),
    ]

    file = models.FileField(upload_to='field_data/uploads/%Y/%m/')
    upload_type = models.CharField(max_length=20, choices=UPLOAD_TYPE_CHOICES)
    field_site = models.ForeignKey(
        FieldSite, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='Auto-detected from sheet name'
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='excel_uploads')
    records_created = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_upload_type_display()} — {self.created_at:%b %d, %Y}"

    class Meta:
        ordering = ['-created_at']


class ApprovalTrackingModel(models.Model):
    """Abstract base model for tracking approval workflow and digital signatures."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('prepared', 'Prepared'),
        ('reviewed', 'Reviewed'),
        ('noted', 'Noted'),
        ('returned', 'Returned'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    prepared_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)
    date_prepared = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)
    date_reviewed = models.DateTimeField(null=True, blank=True)
    noted_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='+', null=True, blank=True)
    date_noted = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class HybridDistribution(ApprovalTrackingModel):
    """
    Hybrid seedling distribution records.
    Matches: Hybrid-Distribution-as-of-Jan.-2026.xlsx
    Columns: Region, Province, District, Municipality, Barangay,
             Farmer Name (Last, First, M.I.), Gender (Male/Female),
             Farm Location (Barangay, Municipality, Province),
             No. of Seedlings Received, Date Received, Type/Variety,
             No. of Seedlings Planted, Date Planted, Remarks
    """
    field_site = models.ForeignKey(FieldSite, on_delete=models.CASCADE, related_name='distributions')
    upload = models.ForeignKey(ExcelUpload, on_delete=models.CASCADE, null=True, blank=True, related_name='distribution_records')
    report_month = models.DateField(help_text='First day of the reporting month')

    region = models.CharField(max_length=20, blank=True)
    province = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=20, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    barangay = models.CharField(max_length=100, blank=True)

    # Farmer name
    farmer_last_name = models.CharField(max_length=100, blank=True, verbose_name='Family Name')
    farmer_first_name = models.CharField(max_length=100, blank=True, verbose_name='Given Name')
    farmer_middle_initial = models.CharField(max_length=10, blank=True, verbose_name='M.I.')

    # Gender
    is_male = models.BooleanField(default=False)
    is_female = models.BooleanField(default=False)

    # Farm Location
    farm_barangay = models.CharField(max_length=100, blank=True, verbose_name='Farm Barangay')
    farm_municipality = models.CharField(max_length=100, blank=True, verbose_name='Farm Municipality')
    farm_province = models.CharField(max_length=100, blank=True, verbose_name='Farm Province')

    # Distribution data
    seedlings_received = models.CharField(max_length=50, blank=True, verbose_name='No. of Seedlings Received')
    date_received = models.DateField(null=True, blank=True)
    variety = models.CharField(max_length=100, blank=True, verbose_name='Type/Variety')
    seedlings_planted = models.PositiveIntegerField(default=0, verbose_name='No. of Seedlings Planted')
    date_planted = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.municipality} — {self.farmer_last_name} ({self.seedlings_received} seedlings)"

    class Meta:
        ordering = ['-report_month', 'municipality']
        verbose_name_plural = 'Hybrid distributions'


class MonthlyHarvest(ApprovalTrackingModel):
    """
    Monthly harvest data — On-Farm Hybrid Seednut Production.
    Matches: Monthly-Harvest-January-2026.xlsx
    Columns: Farm Location, Name of Partner/Farm, Area (Ha.),
             Age of Palms (Years), No. of Hybridized Palms,
             Variety/Hybrid Crosses, Seednuts Produced (OPV/HYBRID),
             Monthly Production Jan-Dec
    """
    field_site = models.ForeignKey(FieldSite, on_delete=models.CASCADE, related_name='harvests')
    upload = models.ForeignKey(ExcelUpload, on_delete=models.CASCADE, null=True, blank=True, related_name='harvest_records')
    report_month = models.DateField(help_text='First day of the reporting month')

    location = models.CharField(max_length=200, blank=True, verbose_name='Farm Location')
    farm_name = models.CharField(max_length=200, blank=True, verbose_name='Name of Partner/Farm')
    area_ha = models.CharField(max_length=20, blank=True, verbose_name='Area (Ha.)')
    age_of_palms = models.CharField(max_length=50, blank=True, verbose_name='Age of Palms (Years)')
    num_hybridized_palms = models.PositiveIntegerField(default=0, verbose_name='No. of Hybridized Palms')
    variety = models.CharField(max_length=200, blank=True, verbose_name='Variety / Hybrid Crosses')
    seednuts_produced = models.CharField(max_length=20, blank=True, verbose_name='Seednuts Produced (OPV/Hybrid)')

    # Monthly production columns (No. of Seednuts)
    production_jan = models.PositiveIntegerField(default=0, verbose_name='Jan')
    production_feb = models.PositiveIntegerField(default=0, verbose_name='Feb')
    production_mar = models.PositiveIntegerField(default=0, verbose_name='Mar')
    production_apr = models.PositiveIntegerField(default=0, verbose_name='Apr')
    production_may = models.PositiveIntegerField(default=0, verbose_name='May')
    production_jun = models.PositiveIntegerField(default=0, verbose_name='Jun')
    production_jul = models.PositiveIntegerField(default=0, verbose_name='Jul')
    production_aug = models.PositiveIntegerField(default=0, verbose_name='Aug')
    production_sep = models.PositiveIntegerField(default=0, verbose_name='Sep')
    production_oct = models.PositiveIntegerField(default=0, verbose_name='Oct')
    production_nov = models.PositiveIntegerField(default=0, verbose_name='Nov')
    production_dec = models.PositiveIntegerField(default=0, verbose_name='Dec')

    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_seednuts(self):
        """Returns the sum of all variety seednut counts for this record."""
        return sum(v.seednuts_count for v in self.varieties.all())

    def __str__(self):
        return f"{self.location} — {self.farm_name}"

    class Meta:
        ordering = ['-report_month']
        verbose_name_plural = 'Monthly harvests'


class HarvestVariety(models.Model):
    """
    Child model: one harvest record can have multiple variety rows.
    E.g. Loay has 2 varieties, Balilihan has 3.
    """
    harvest = models.ForeignKey(MonthlyHarvest, on_delete=models.CASCADE, related_name='varieties')
    variety = models.CharField(max_length=200, verbose_name='Variety / Hybrid Crosses')
    seednuts_type = models.CharField(max_length=20, blank=True, verbose_name='Seednuts Produced (OPV/Hybrid)')
    seednuts_count = models.PositiveIntegerField(default=0, verbose_name='Seednuts Produced Count')
    remarks = models.CharField(max_length=255, blank=True, verbose_name='Remarks')

    class Meta:
        ordering = ['pk']
        verbose_name_plural = 'Harvest varieties'

    def __str__(self):
        return f"{self.variety} ({self.seednuts_type})"

class NurseryOperation(ApprovalTrackingModel):
    """
    Nursery operations / communal nursery establishment records.
    Matches: Nursery-Operations-and-Terminal-Report-January-2026.xlsx
    Columns: Region/Province/District, Barangay/Municipality,
             Name of Proponent (Entity, Representative),
             Target No. of Seednuts, No. Harvested, Date Harvested,
             Date Received, Source of Seednuts, Type/Variety,
             No. Sown, Date Sown, No. Germinated, No. Ungerminated,
             No. Culled Seedlings, No. Good Seedlings @1ft,
             No. Ready to Plant (Polybagged), No. Dispatched
    """
    REPORT_TYPE_CHOICES = [
        ('operation', 'Monthly Report'),
        ('terminal', 'Terminal Report'),
    ]

    field_site = models.ForeignKey(FieldSite, on_delete=models.CASCADE, related_name='nursery_ops')
    upload = models.ForeignKey(ExcelUpload, on_delete=models.CASCADE, null=True, blank=True, related_name='nursery_records')
    report_month = models.DateField(help_text='First day of the reporting month')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='operation')

    region_province_district = models.CharField(max_length=100, blank=True, verbose_name='Region / Province / District')
    barangay_municipality = models.CharField(max_length=200, blank=True, verbose_name='Barangay / Municipality')
    proponent_entity = models.CharField(max_length=200, blank=True, verbose_name='Proponent Entity Name')
    proponent_representative = models.CharField(max_length=200, blank=True, verbose_name='Representative')
    target_seednuts = models.PositiveIntegerField(default=0, verbose_name='Target No. of Seednuts')

    # Terminal-report-specific fields
    nursery_start_date = models.DateField(null=True, blank=True, verbose_name='Nursery Start Date',
                                          help_text='Date when seednuts were first sown in the nursery')
    date_ready_for_distribution = models.DateField(null=True, blank=True, verbose_name='Date Ready for Distribution',
                                                    help_text='Date when seedlings became ready for planting')
    distribution_remarks = models.TextField(blank=True, verbose_name='Distribution Remarks',
                                             help_text='Final distribution notes/summary for terminal report')

    def __str__(self):
        return f"{self.proponent_entity} — target: {self.target_seednuts}"

    class Meta:
        ordering = ['-report_month', 'proponent_entity']
        verbose_name_plural = 'Nursery operations'


class NurseryBatch(models.Model):
    """
    Child model: one nursery operation can have multiple harvest batches.
    Each batch represents a single harvest event with shared info
    (date harvested, source, total seednuts harvested).
    """
    nursery = models.ForeignKey(NurseryOperation, on_delete=models.CASCADE, related_name='batches')
    seednuts_harvested = models.PositiveIntegerField(default=0, verbose_name='No. of Seednuts Harvested')
    date_harvested = models.CharField(max_length=50, blank=True, verbose_name='Date Harvested')
    date_received = models.CharField(max_length=50, blank=True, verbose_name='Date Seednuts Received')
    source_of_seednuts = models.CharField(max_length=200, blank=True, verbose_name='Source of Seednuts')

    class Meta:
        ordering = ['pk']
        verbose_name_plural = 'Nursery batches'

    def __str__(self):
        return f"Batch: {self.seednuts_harvested} seednuts — {self.date_harvested}"


class NurseryBatchVariety(models.Model):
    """
    Grandchild model: each batch can have multiple variety rows.
    E.g. PCA 15-10 and PCA 15-1 within the same harvest batch.
    """
    batch = models.ForeignKey(NurseryBatch, on_delete=models.CASCADE, related_name='varieties')
    variety = models.CharField(max_length=100, blank=True, verbose_name='Type / Variety')
    seednuts_sown = models.PositiveIntegerField(default=0, verbose_name='No. of Seednuts Sown')
    date_sown = models.CharField(max_length=50, blank=True, verbose_name='Date Seednut Sown')
    seedlings_germinated = models.PositiveIntegerField(default=0, verbose_name='No. of Seedlings Germinated')
    ungerminated_seednuts = models.PositiveIntegerField(default=0, verbose_name='No. of Ungerminated Seednuts')
    culled_seedlings = models.PositiveIntegerField(default=0, verbose_name='No. of Culled Seedlings')
    good_seedlings = models.PositiveIntegerField(default=0, verbose_name='No. of Good Seedlings @ 1 ft tall')
    ready_to_plant = models.PositiveIntegerField(default=0, verbose_name='No. of Ready to Plant (Polybagged)')
    seedlings_dispatched = models.PositiveIntegerField(default=0, verbose_name='No. of Seedlings Dispatched')
    remarks = models.CharField(max_length=255, blank=True, verbose_name='Remarks')

    class Meta:
        ordering = ['pk']
        verbose_name_plural = 'Nursery batch varieties'

    def __str__(self):
        return f"{self.variety} — Sown: {self.seednuts_sown}"


class PollenProduction(ApprovalTrackingModel):
    """
    Pollen production and inventory records.
    Matches: Pollen-Prod-Inventory-January-2026.xlsx
    Columns: Month, Ending Balance Last Month, Pollens Received
             (Source, Date, Amount), Weekly Utilization (Week 1-5),
             Total Utilization, Ending Balance
    """
    field_site = models.ForeignKey(FieldSite, on_delete=models.CASCADE, related_name='pollen_records')
    upload = models.ForeignKey(ExcelUpload, on_delete=models.CASCADE, null=True, blank=True, related_name='pollen_records_set')
    report_month = models.DateField(help_text='First day of the reporting month')

    month_label = models.CharField(max_length=20, blank=True, verbose_name='Month')
    pollen_variety = models.CharField(max_length=200, blank=True, verbose_name='Pollen Variety')
    ending_balance_prev = models.CharField(max_length=50, blank=True, verbose_name='Ending Balance Last Month')

    # Pollens received from other center
    pollen_source = models.CharField(max_length=200, blank=True, verbose_name='Source')
    date_received = models.CharField(max_length=50, blank=True, verbose_name='Date Received')
    pollens_received = models.CharField(max_length=50, blank=True, verbose_name='Amount of Pollens Received')

    # Weekly utilization
    week1 = models.CharField(max_length=20, blank=True, verbose_name='Week 1')
    week2 = models.CharField(max_length=20, blank=True, verbose_name='Week 2')
    week3 = models.CharField(max_length=20, blank=True, verbose_name='Week 3')
    week4 = models.CharField(max_length=20, blank=True, verbose_name='Week 4')
    week5 = models.CharField(max_length=20, blank=True, verbose_name='Week 5')
    total_utilization = models.CharField(max_length=20, blank=True, verbose_name='Total Utilization')

    ending_balance = models.CharField(max_length=50, blank=True, verbose_name='Ending Balance')
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.field_site} — {self.month_label}"

    class Meta:
        ordering = ['-report_month']
        verbose_name_plural = 'Pollen production records'
