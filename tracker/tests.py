from io import BytesIO
import re
import unittest

from sqlalchemy import Text
from openpyxl import load_workbook

from app import create_app
from tracker.extensions import db
from tracker.models import (
    AuditLog,
    Contact,
    DataCollection,
    DataTask,
    DataTaskAssignment,
    User,
)


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

    def test_password_column_accepts_unbounded_hashes(self):
        self.assertIsInstance(User.__table__.c.password.type, Text)

    def test_bootstrap_admin_stores_password_hash(self):
        db.session.delete(self.admin)
        db.session.commit()

        result = self.app.test_cli_runner().invoke(args=["bootstrap-admin"])

        self.assertEqual(result.exit_code, 0, result.output)
        admin = db.session.scalar(db.select(User).where(User.mobile == "7338884040"))
        self.assertGreater(len(admin.password), 128)

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
        api_response = self.client.get("/api/contacts/export.xlsx")
        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(api_response.mimetype, response.mimetype)

    def test_next_api_authenticates_and_returns_dashboard_data(self):
        unauthenticated = self.client.get("/api/dashboard")
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(unauthenticated.get_json()["error"], "Please sign in to continue.")

        login_response = self.client.post(
            "/api/login",
            json={"mobile": self.admin.mobile},
        )
        self.assertEqual(login_response.status_code, 200)
        dashboard = self.client.get("/api/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        payload = dashboard.get_json()
        self.assertTrue(payload["user"]["isAdmin"])
        self.assertEqual(payload["stats"]["total"], 1)
        self.assertEqual(payload["contacts"][0]["name"], "Contact")
        self.assertEqual(payload["memberStats"][0]["total"], 1)

    def test_next_api_preserves_contact_ownership_and_status_validation(self):
        self.client.post("/api/login", json={"mobile": self.member.mobile})
        denied = self.client.post(
            "/api/contacts/99999/status",
            json={"status": "success", "destination": "chennai"},
        )
        self.assertEqual(denied.status_code, 404)

        invalid = self.client.post(
            f"/api/contacts/{self.contact.id}/status",
            json={"status": "success", "destination": ""},
        )
        self.assertEqual(invalid.status_code, 400)

        updated = self.client.post(
            f"/api/contacts/{self.contact.id}/status",
            json={"status": "success", "destination": "chennai"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["contact"]["destinationDisplay"], "Chennai")

    def test_next_api_can_import_contacts(self):
        self.client.post("/api/login", json={"mobile": self.admin.mobile})
        response = self.client.post(
            "/api/contacts/import",
            data={
                "file": (
                    BytesIO(b"name,phone\nAPI Contact,9876543210\n"),
                    "contacts.csv",
                )
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["created"], 1)
        imported = db.session.query(Contact).filter_by(phone="+919876543210").one()
        self.assertEqual(imported.assigned_to_id, self.member.id)

    def test_health_endpoint_checks_backend_database(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_admin_can_edit_and_remove_member_without_losing_assignment_history(self):
        self.client.post("/api/login", json={"mobile": self.admin.mobile})
        updated = self.client.patch(
            f"/api/members/{self.member.id}",
            json={"displayName": "Updated Member", "mobile": "9888888889"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["member"]["name"], "Updated Member")

        removed = self.client.post(f"/api/members/{self.member.id}/deactivate")
        self.assertEqual(removed.status_code, 200)
        db.session.refresh(self.contact)
        self.assertEqual(self.contact.assigned_to_id, self.member.id)

    def test_admin_assigns_configurable_task_and_member_collects_data(self):
        self.client.post("/api/login", json={"mobile": self.admin.mobile})
        created = self.client.post(
            "/api/tasks",
            json={
                "title": "Data Collection Task",
                "instructions": "Collect the household information.",
                "memberIds": [self.member.id],
                "fields": [
                    {
                        "key": "occupation",
                        "label": "Occupation",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
        )
        self.assertEqual(created.status_code, 201)
        task_id = created.get_json()["task"]["id"]

        self.client.post("/api/logout")
        self.client.post("/api/login", json={"mobile": self.member.mobile})
        member_tasks = self.client.get("/api/tasks")
        self.assertEqual([task["id"] for task in member_tasks.get_json()["tasks"]], [task_id])
        self.assertTrue(self.client.get("/api/dashboard").get_json()["requiresCollection"])
        bypass = self.client.post(
            f"/api/contacts/{self.contact.id}/status",
            json={"status": "success", "destination": "chennai"},
        )
        self.assertEqual(bypass.status_code, 400)

        missing_required = self.client.post(
            f"/api/tasks/{task_id}/submissions",
            json={
                "contactId": self.contact.id,
                "age": 21,
                "area": "Ayanavaram",
                "fields": {"occupation": ""},
            },
        )
        self.assertEqual(missing_required.status_code, 400)

        submitted = self.client.post(
            f"/api/tasks/{task_id}/submissions",
            json={
                "contactId": self.contact.id,
                "age": 21,
                "area": "Ayanavaram",
                "fields": {"occupation": "Teacher"},
            },
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.get_json()["classification"], "kilpauk")
        self.assertEqual(self.contact.destination, "kilpauk")
        saved = db.session.query(DataCollection).filter_by(task_id=task_id).one()
        self.assertEqual(saved.age, 21)
        self.assertEqual(saved.area, "Ayanavaram")
        self.assertEqual(saved.fields_json, '{"occupation": "Teacher"}')

        general_success = self.client.post(
            f"/api/tasks/{task_id}/submissions",
            json={
                "contactId": self.contact.id,
                "age": 18,
                "area": "Chennai",
                "fields": {"occupation": "Student"},
            },
        )
        self.assertEqual(general_success.get_json()["classification"], "success")
        self.assertEqual(self.contact.status, "success")
        self.assertEqual(self.contact.destination, "other")

        self.client.post("/api/logout")
        self.client.post("/api/login", json={"mobile": self.admin.mobile})
        export = self.client.get("/api/contacts/export.xlsx")
        workbook = load_workbook(BytesIO(export.data), read_only=True, data_only=True)
        collected = list(workbook["Data Collection"].values)
        self.assertIn("Occupation", collected[0][-1])
        self.assertEqual(collected[-1][-1], "Student")

    def test_age_over_21_takes_priority_over_kilpauk_area(self):
        self.client.post("/api/login", json={"mobile": self.admin.mobile})
        task_response = self.client.post(
            "/api/tasks",
            json={
                "title": "Age and area",
                "instructions": "Ask age and location.",
                "memberIds": [self.member.id],
                "fields": [],
            },
        )
        task_id = task_response.get_json()["task"]["id"]
        self.client.post("/api/logout")
        self.client.post("/api/login", json={"mobile": self.member.mobile})
        response = self.client.post(
            f"/api/tasks/{task_id}/submissions",
            json={
                "contactId": self.contact.id,
                "age": 22,
                "area": "Kilpauk",
                "fields": {},
            },
        )
        self.assertEqual(response.get_json()["classification"], "typ")
        self.assertEqual(self.contact.destination, "typ")

    def test_task_can_be_edited_disabled_and_re_enabled(self):
        self.client.post("/api/login", json={"mobile": self.admin.mobile})
        data = {
            "title": "Initial task",
            "instructions": "Ask and record.",
            "memberIds": [self.member.id],
            "fields": [],
        }
        created = self.client.post("/api/tasks", json=data)
        task_id = created.get_json()["task"]["id"]

        data["title"] = "Updated task"
        updated = self.client.patch(f"/api/tasks/{task_id}", json=data)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["task"]["title"], "Updated task")
        self.assertEqual(
            db.session.query(DataTaskAssignment).filter_by(task_id=task_id).count(),
            1,
        )

        disabled = self.client.delete(f"/api/tasks/{task_id}")
        self.assertEqual(disabled.status_code, 200)
        self.client.post("/api/logout")
        self.client.post("/api/login", json={"mobile": self.member.mobile})
        self.assertEqual(self.client.get("/api/tasks").get_json()["tasks"], [])

        self.client.post("/api/logout")
        self.client.post("/api/login", json={"mobile": self.admin.mobile})
        enabled = self.client.post(f"/api/tasks/{task_id}/enable")
        self.assertEqual(enabled.status_code, 200)
        self.assertTrue(enabled.get_json()["task"]["active"])

    def test_next_api_requires_csrf_token(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        token = self.client.get("/api/csrf").get_json()["csrfToken"]
        rejected = self.client.post(
            "/api/login",
            json={"mobile": self.admin.mobile},
        )
        self.assertEqual(rejected.status_code, 400)
        accepted = self.client.post(
            "/api/login",
            json={"mobile": self.admin.mobile},
            headers={"X-CSRFToken": token},
        )
        self.assertEqual(accepted.status_code, 200)

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
