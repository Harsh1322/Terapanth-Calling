from django import forms
from .models import User


class MobileLoginForm(forms.Form):
    mobile = forms.CharField(
        label="Mobile number",
        widget=forms.TextInput(attrs={"autocomplete": "username", "placeholder": "Mobile number"}),
    )
    password = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
class MemberForm(forms.Form):
    mobile = forms.CharField(max_length=20)
    display_name = forms.CharField(max_length=120)
    password = forms.CharField(min_length=8, widget=forms.PasswordInput())
