from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Contact, AuditLog
@admin.register(User)
class TrackerUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Committee details", {"fields": ("mobile", "is_committee_member")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Committee details", {"fields": ("mobile", "is_committee_member")}),)
    list_display = ("mobile", "username", "is_staff", "is_committee_member", "is_active")
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "assigned_to", "status", "destination")
    search_fields = ("name", "phone")
@admin.register(AuditLog)
class AuditAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "contact")
    readonly_fields = ("created_at", "actor", "contact", "action", "details")
