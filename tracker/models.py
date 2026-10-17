from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    mobile = models.CharField(max_length=20, unique=True)
    is_committee_member = models.BooleanField(default=False)
    USERNAME_FIELD = "mobile"
    REQUIRED_FIELDS = ["username"]

class Contact(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("no_answer", "Call didn't pick up"),
        ("invalid", "Number invalid"),
        ("follow_up", "Need to follow up"),
    ]
    DESTINATION_CHOICES = [("chennai", "Chennai"), ("kilpauk", "Kilpauk"), ("typ", "TYP")]
    name = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=30, unique=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="contacts")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    destination = models.CharField(max_length=20, choices=DESTINATION_CHOICES, blank=True)
    notes = models.CharField(max_length=500, blank=True)
    source_group = models.CharField(max_length=180, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
