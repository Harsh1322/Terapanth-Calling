from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash

from .extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "tracker_user"

    id = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.Text, nullable=False, default="")
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
        ("typ_member", "TYP member"),
        ("kilpauk_member", "Kilpauk member"),
        ("success", "Success"),
        ("no_answer", "Call didn't pick up"),
        ("invalid", "Number invalid"),
        ("follow_up", "Need to follow up"),
    ]
    DESTINATION_CHOICES = [
        ("chennai", "Chennai"),
        ("kilpauk", "Kilpauk"),
        ("typ", "TYP"),
        ("other", "Other / data collected"),
    ]

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


class DataTask(db.Model):
    __tablename__ = "tracker_data_task"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    instructions = db.Column(db.Text, nullable=False, default="")
    fields_json = db.Column(db.Text, nullable=False, default="[]")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    created_by_id = db.Column(db.Integer, db.ForeignKey("tracker_user.id"), nullable=True)

    created_by = db.relationship("User")
    assignments = db.relationship(
        "DataTaskAssignment", back_populates="task", cascade="all, delete-orphan"
    )
    submissions = db.relationship("DataCollection", back_populates="task")


class DataTaskAssignment(db.Model):
    __tablename__ = "tracker_data_task_assignment"
    __table_args__ = (
        db.UniqueConstraint("task_id", "member_id", name="uq_task_member_assignment"),
    )

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer, db.ForeignKey("tracker_data_task.id"), nullable=False, index=True
    )
    member_id = db.Column(db.Integer, db.ForeignKey("tracker_user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    task = db.relationship("DataTask", back_populates="assignments")
    member = db.relationship("User")


class DataCollection(db.Model):
    __tablename__ = "tracker_data_collection"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer, db.ForeignKey("tracker_data_task.id"), nullable=False, index=True
    )
    contact_id = db.Column(
        db.Integer, db.ForeignKey("tracker_contact.id"), nullable=False, index=True
    )
    member_id = db.Column(db.Integer, db.ForeignKey("tracker_user.id"), nullable=False)
    task_title = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    area = db.Column(db.String(120), nullable=False)
    classification = db.Column(db.String(20), nullable=False)
    fields_json = db.Column(db.Text, nullable=False, default="{}")
    field_labels_json = db.Column(db.Text, nullable=False, default="{}")
    submitted_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    task = db.relationship("DataTask", back_populates="submissions")
    contact = db.relationship("Contact")
    member = db.relationship("User")
