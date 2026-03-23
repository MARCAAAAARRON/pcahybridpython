from django import forms
from .models import HybridizationRecord, RecordImage


class HybridizationRecordForm(forms.ModelForm):
    class Meta:
        model = HybridizationRecord
        fields = [
            'crop_type', 'parent_line_a', 'parent_line_b',
            'hybrid_code', 'date_planted', 'growth_status', 'notes',
        ]
        widgets = {
            'date_planted': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'crop_type': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_line_a': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_line_b': forms.TextInput(attrs={'class': 'form-control'}),
            'hybrid_code': forms.TextInput(attrs={'class': 'form-control'}),
            'growth_status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RecordImageForm(forms.ModelForm):
    class Meta:
        model = RecordImage
        fields = ['image', 'caption']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Image caption'}),
        }
