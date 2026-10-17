from django.test import TestCase
from django.urls import reverse

from .models import Contact, User


class LoginAndContactFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="Admin", mobile="7338884040", password="unused"
        )
        self.member = User.objects.create_user(
            username="Member", mobile="9888888888", password="member-password", is_committee_member=True
        )
        self.contact = Contact.objects.create(name="Contact", phone="+919999999999", assigned_to=self.member)

    def test_admin_can_sign_in_with_mobile_only(self):
        response = self.client.post(reverse("login"), {"mobile": "7338884040", "password": ""})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(self.client.get(reverse("dashboard")), "All committee contacts and progress")

    def test_member_can_sign_in_with_mobile_only_and_update_assigned_contact(self):
        response = self.client.post(reverse("login"), {"mobile": self.member.mobile})
        self.assertRedirects(response, reverse("dashboard"))
        updated = self.client.post(
            reverse("update_status", args=[self.contact.id]),
            {"status": "success", "destination": "chennai", "notes": "Confirmed"},
        )
        self.assertRedirects(updated, reverse("dashboard"))
        self.contact.refresh_from_db()
        self.assertEqual((self.contact.status, self.contact.destination), ("success", "chennai"))
