from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "tracker_user"

    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.String(128), nullable=False, default="")
    last_login = db.Column(db.DateTime, nullable=True)
    is_superuser = db.Column(db.Boolean, nullable=False, default=False)
    username = db.Column(db.String(150), nullable=False, unique=True)
    first_name = db.Column(db.String(150), nullable=False, default="")
    last_name = db.Column(db.String(150), nullable=False, default="")
    email = db.Column(db.String(254), nullable=False, default="")
    is_staff = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    date_joined = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    mobile = db.Column(db.String(20), nullable=False, unique=True)
    is_committee_member = db.Column(db.Boolean, nullable=False, default=False)

    contacts = db.relationship("Contact", back_populates="assigned_to")

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)


class Contact(db.Model):
    __tablename__ = "tracker_contact"

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("success", "Success"),
        ("no_answer", "Call didn't pick up"),
        ("invalid", "Number invalid"),
        ("follow_up", "Need to follow up"),
    ]
    DESTINATION_CHOICES = [("chennai", "Chennai"), ("kilpauk", "Kilpauk"), ("typ", "TYP")]

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False, default="")
    phone = db.Column(db.String(30), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    destination = db.Column(db.String(20), nullable=False, default="")
    notes = db.Column(db.String(500), nullable=False, default="")
    source_group = db.Column(db.String(180), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("tracker_user.id"), nullable=True)

    assigned_to = db.relationship("User", back_populates="contacts")

    @property
    def status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def destination_display(self):
        return dict(self.DESTINATION_CHOICES).get(self.destination, self.destination)


class AuditLog(db.Model):
    __tablename__ = "tracker_auditlog"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    actor_id = db.Column(db.Integer, db.ForeignKey("tracker_user.id"), nullable=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("tracker_contact.id"), nullable=True)

    actor = db.relationship("User")
    contact = db.relationship("Contact")
