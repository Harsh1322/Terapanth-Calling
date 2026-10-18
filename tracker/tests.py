from io import BytesIO
import re
import unittest

from app import create_app
from tracker.extensions import db
from tracker.models import AuditLog, Contact, User


class LoginAndContactFlowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "WTF_CSRF_ENABLED": False,
                "SESSION_COOKIE_SECURE": False,
            }
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.admin = User(
            username="Admin",
            mobile="7338884040",
            is_superuser=True,
            is_staff=True,
        )
        self.admin.set_password("not-used-for-mobile-login")
        self.member = User(
            username="Member",
            mobile="9888888888",
            is_committee_member=True,
        )
        self.member.set_password("temporary-password")
        db.session.add_all([self.admin, self.member])
        db.session.flush()
        self.contact = Contact(
            name="Contact",
            phone="+919999999999",
            assigned_to=self.member,
        )
        db.session.add(self.contact)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_admin_can_sign_in_with_mobile_only(self):
        response = self.client.post("/login/", data={"mobile": "7338884040"})
        self.assertEqual(response.status_code, 302)
        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"All committee contacts and progress", dashboard.data)

    def test_member_can_sign_in_and_update_assigned_contact(self):
        response = self.client.post("/login/", data={"mobile": self.member.mobile})
        self.assertEqual(response.status_code, 302)
        updated = self.client.post(
            f"/contacts/{self.contact.id}/status/",
            data={
                "status": "success",
                "destination": "chennai",
                "notes": "Confirmed",
            },
        )
        self.assertEqual(updated.status_code, 302)
        db.session.refresh(self.contact)
        self.assertEqual(
            (self.contact.status, self.contact.destination, self.contact.notes),
            ("success", "chennai", "Confirmed"),
        )
        self.assertEqual(
            db.session.query(AuditLog).filter_by(action="status_updated").count(),
            1,
        )

    def test_member_cannot_update_another_members_contact(self):
        other_member = User(username="Other", mobile="9777777777", is_committee_member=True)
        db.session.add(other_member)
        db.session.flush()
        other_contact = Contact(name="Private", phone="+919888888888", assigned_to=other_member)
        db.session.add(other_contact)
        db.session.commit()
        self.client.post("/login/", data={"mobile": self.member.mobile})
        response = self.client.post(
            f"/contacts/{other_contact.id}/status/",
            data={"status": "invalid"},
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_export_xlsx(self):
        self.client.post("/login/", data={"mobile": self.admin.mobile})
        response = self.client.get("/contacts/export.xlsx")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("committee_contacts.xlsx", response.headers["Content-Disposition"])

    def test_admin_can_add_member(self):
        self.client.post("/login/", data={"mobile": self.admin.mobile})
        response = self.client.post(
            "/members/",
            data={
                "display_name": "New Member",
                "mobile": "9666666666",
                "password": "temporary-password",
            },
        )
        self.assertEqual(response.status_code, 302)
        member = db.session.query(User).filter_by(mobile="9666666666").one()
        self.assertTrue(member.is_committee_member)
        self.assertEqual(member.username, "New Member")

    def test_admin_can_import_csv_and_assign_contacts(self):
        self.client.post("/login/", data={"mobile": self.admin.mobile})
        response = self.client.post(
            "/contacts/import/",
            data={
                "file": (
                    BytesIO(b"name,phone,group\nImported Contact,9876543210,Group A\n"),
                    "contacts.csv",
                )
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        imported = db.session.query(Contact).filter_by(phone="+919876543210").one()
        self.assertEqual(imported.assigned_to_id, self.member.id)
        self.assertEqual(imported.source_group, "Group A")

    def test_csrf_is_required_for_post_requests(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post("/login/", data={"mobile": self.admin.mobile})
        self.assertEqual(response.status_code, 400)
        login_page = self.client.get("/login/")
        token = re.search(rb'name="csrf_token" value="([^"]+)"', login_page.data)
        self.assertIsNotNone(token)
        response = self.client.post(
            "/login/",
            data={"mobile": self.admin.mobile, "csrf_token": token.group(1).decode()},
        )
        self.assertEqual(response.status_code, 302)


if __name__ == "__main__":
    unittest.main()
