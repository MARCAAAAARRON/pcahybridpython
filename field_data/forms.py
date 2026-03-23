from django import forms
from .models import HybridDistribution, MonthlyHarvest, NurseryOperation, PollenProduction, NurseryBatch, NurseryBatchVariety


class HybridDistributionForm(forms.ModelForm):
    """Form for hybrid distribution records — matches PCA Excel format."""
    class Meta:
        model = HybridDistribution
        fields = [
            'report_month', 'region', 'province', 'district', 'municipality',
            'barangay', 'farmer_last_name', 'farmer_first_name', 'farmer_middle_initial',
            'is_male', 'is_female',
            'farm_barangay', 'farm_municipality', 'farm_province',
            'seedlings_received', 'date_received', 'variety',
            'seedlings_planted', 'date_planted', 'remarks',
        ]
        widgets = {
            'report_month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. VII'}),
            'province': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. BOHOL'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. III'}),
            'municipality': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'farmer_last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'farmer_first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'farmer_middle_initial': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. M.'}),
            'is_male': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_female': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'farm_barangay': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_municipality': forms.TextInput(attrs={'class': 'form-control'}),
            'farm_province': forms.TextInput(attrs={'class': 'form-control'}),
            'seedlings_received': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'date_received': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'variety': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. PCA 15-10'}),
            'seedlings_planted': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'date_planted': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class MonthlyHarvestForm(forms.ModelForm):
    """Form for monthly harvest / seednut production records."""
    class Meta:
        model = MonthlyHarvest
        fields = [
            'report_month', 'location', 'farm_name', 'area_ha',
            'age_of_palms', 'num_hybridized_palms',
            'remarks',
        ]
        widgets = {
            'report_month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Brgy. Boctol, Balilihan, Bohol'}),
            'farm_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Violo Llorente, Sr.'}),
            'area_ha': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3.62'}),
            'age_of_palms': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 16'}),
            'num_hybridized_palms': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class NurseryOperationForm(forms.ModelForm):
    """Form for nursery operation / communal nursery records."""
    class Meta:
        model = NurseryOperation
        fields = [
            'report_month', 'report_type',
            'region_province_district', 'barangay_municipality',
            'proponent_entity', 'proponent_representative',
            'target_seednuts',
            'nursery_start_date', 'date_ready_for_distribution',
            'distribution_remarks',
        ]
        widgets = {
            'report_month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'region_province_district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. VII-Bohol/III'}),
            'barangay_municipality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Balilihan'}),
            'proponent_entity': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Balilihan On-Farm'}),
            'proponent_representative': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Epigenio M. Mahinay'}),
            'target_seednuts': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'nursery_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_ready_for_distribution': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'distribution_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Final distribution notes...'}),
        }


class NurseryBatchForm(forms.ModelForm):
    class Meta:
        model = NurseryBatch
        fields = [
            'seednuts_harvested', 'date_harvested',
            'date_received', 'source_of_seednuts',
        ]
        widgets = {
            'seednuts_harvested': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'date_harvested': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. August 27, 2025'}),
            'date_received': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. August 28, 2025'}),
            'source_of_seednuts': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Balilihan On-Farm'}),
        }


class NurseryBatchVarietyForm(forms.ModelForm):
    class Meta:
        model = NurseryBatchVariety
        fields = [
            'variety', 'seednuts_sown', 'date_sown',
            'seedlings_germinated', 'ungerminated_seednuts', 'culled_seedlings',
            'good_seedlings', 'ready_to_plant', 'seedlings_dispatched',
            'remarks',
        ]
        widgets = {
            'variety': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. PCA 15-10'}),
            'seednuts_sown': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'date_sown': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. September 11, 2025'}),
            'seedlings_germinated': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'ungerminated_seednuts': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'culled_seedlings': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'good_seedlings': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'ready_to_plant': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'seedlings_dispatched': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'remarks': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }


MONTH_CHOICES = [
    ('', '— Select Month —'),
    ('Jan', 'Jan'), ('Feb', 'Feb'), ('Mar', 'Mar'),
    ('Apr', 'Apr'), ('May', 'May'), ('Jun', 'Jun'),
    ('Jul', 'Jul'), ('Aug', 'Aug'), ('Sep', 'Sep'),
    ('Oct', 'Oct'), ('Nov', 'Nov'), ('Dec', 'Dec'),
]

class PollenProductionForm(forms.ModelForm):
    """Form for pollen production and inventory records."""
    month_label = forms.ChoiceField(
        choices=MONTH_CHOICES, required=False, 
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = PollenProduction
        fields = [
            'report_month', 'month_label', 'pollen_variety', 'ending_balance_prev',
            'pollen_source', 'date_received', 'pollens_received',
            'week1', 'week2', 'week3', 'week4', 'week5',
            'total_utilization', 'ending_balance', 'remarks',
        ]
        widgets = {
            'report_month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'pollen_variety': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. LAGUNA TALL POLLENS'}),
            'ending_balance_prev': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'pollen_source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CVSPC'}),
            'date_received': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'pollens_received': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'week1': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'week2': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'week3': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'week4': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'week5': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'total_utilization': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'ending_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
