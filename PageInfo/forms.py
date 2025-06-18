from django import forms
from .models import PageGroup

class PageURLForm(forms.Form):
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('tiktok', 'TikTok'),
        ('instagram', 'Instagram'),
        ('lemon8', 'Lemon8'),
    ]
    platform = forms.ChoiceField(
        choices=PLATFORM_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control form-control-lg',
        }),
        required=True,  # บังคับเลือก platform
        label="Platform"
    )
    url = forms.URLField(
        label="Page URL",
        widget=forms.URLInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Input URL Page'
        })
    )

class PageGroupForm(forms.ModelForm):
    class Meta:
        model = PageGroup
        fields = ['group_name']
        widgets = {
            'group_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Input Group Name'
            }),
        }
