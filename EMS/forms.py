
from django import forms
from .models import EmployeeAddress


class EmployeeAddressForm(forms.ModelForm):

    class Meta:
        model = EmployeeAddress

        fields = [
            "address_type",
            "address_line1",
            "address_line2",
            "city",
            "district",
            "state",
            "postal_code",
            "country",
        ]

        widgets = {
            "address_type": forms.Select(attrs={
                "class": "form-control",
            }),
            "address_line1": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter address line 1",
            }),
            "address_line2": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter address line 2 (optional)",
            }),
            "city": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter city",
            }),
            "district": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter district",
            }),
            "state": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter state",
            }),
            "postal_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter postal code",
            }),
            "country": forms.TextInput(attrs={
                "class": "form-control",
            }),
        }
