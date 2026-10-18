import csv
import io
import json
import re
from functools import wraps
from zipfile import BadZipFile

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy import func, select

from .extensions import db
from .models import AuditLog, Contact, User

tracker = Blueprint("tracker", __name__)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_superuser:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@tracker.route("/login/", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("tracker.dashboard"))
    error = None
    mobile_value = ""
    if request.method == "POST":
        mobile_value = request.form.get("mobile", "")
        mobile = re.sub(r"\D", "", mobile_value)
        user = db.session.scalar(
            select(User).where(User.mobile == mobile, User.is_active.is_(True))
        )
        if user is None:
            error = "No active account uses that mobile number."
        else:
            login_user(user)
            return redirect(url_for("tracker.dashboard"))
    return render_template("login.html", error=error, mobile=mobile_value)


@tracker.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for("tracker.login"))


@tracker.route("/")
@login_required
def dashboard():
    stats_query = select(Contact.status, func.count(Contact.id)).group_by(Contact.status)
    contact_query = select(Contact).order_by(Contact.name, Contact.phone).limit(500)
    if not current_user.is_superuser:
        stats_query = stats_query.where(Contact.assigned_to_id == current_user.id)
        contact_query = contact_query.where(Contact.assigned_to_id == current_user.id)
    status_counts = dict(db.session.execute(stats_query).all())
    stats = {
        "total": sum(status_counts.values()),
        "pending": status_counts.get("pending", 0),
        "success": status_counts.get("success", 0),
        "no_answer": status_counts.get("no_answer", 0),
        "invalid": status_counts.get("invalid", 0),
        "follow_up": status_counts.get("follow_up", 0),
    }
    contacts = db.session.scalars(contact_query).all()
    members = db.session.scalars(
        select(User)
        .where(User.is_committee_member.is_(True), User.is_active.is_(True))
        .order_by(User.username)
    ).all()
    member_stats = []
    if current_user.is_superuser:
        assignment_counts = {}
        results = db.session.execute(
            select(Contact.assigned_to_id, Contact.status, func.count(Contact.id))
            .group_by(Contact.assigned_to_id, Contact.status)
        ).all()
        for member_id, status, count in results:
            assignment_counts.setdefault(member_id, {})[status] = count
        for member in members:
            counts = assignment_counts.get(member.id, {})
            member_stats.append(
                {
                    "member": member,
                    "total": sum(counts.values()),
                    "success": counts.get("success", 0),
                    "pending": sum(
                        counts.get(status, 0)
                        for status in ("pending", "follow_up", "no_answer")
                    ),
                    "invalid": counts.get("invalid", 0),
                }
            )
    return render_template(
        "dashboard.html",
        contacts=contacts,
        stats=stats,
        member_stats=member_stats,
    )


@tracker.route("/members/", methods=["GET", "POST"])
@admin_required
def members():
    if request.method == "POST":
        mobile = re.sub(r"\D", "", request.form.get("mobile", ""))
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        if (
            not mobile
            or len(mobile) > 20
            or not display_name
            or len(display_name) > 150
        ):
            flash("Enter a valid mobile number and a name of at most 150 characters.", "error")
        elif len(password) < 8:
            flash("The password must contain at least 8 characters.", "error")
        elif db.session.scalar(select(User.id).where(User.mobile == mobile)) is not None:
            flash("A user with that mobile number already exists.", "error")
        else:
            user = User(
                username=display_name,
                mobile=mobile,
                is_committee_member=True,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.add(
                AuditLog(
                    actor=current_user,
                    action="member_added",
                    details=f"Added member {mobile}",
                )
            )
            db.session.commit()
            flash(f"Member {mobile} created.", "success")
            return redirect(url_for("tracker.members"))
    member_list = db.session.scalars(
        select(User)
        .where(User.is_committee_member.is_(True))
        .order_by(User.username)
    ).all()
    return render_template("members.html", members=member_list)


@tracker.route("/members/<int:user_id>/delete/", methods=["POST"])
@admin_required
def delete_member(user_id):
    user = db.session.scalar(
        select(User).where(
            User.id == user_id,
            User.is_committee_member.is_(True),
        )
    )
    if user is None:
        abort(404)
    mobile = user.mobile
    user.is_active = False
    db.session.add(
        AuditLog(
            actor=current_user,
            action="member_deactivated",
            details=f"Deactivated {mobile}; contact ownership retained",
        )
    )
    db.session.commit()
    flash("Member deactivated. Existing assignments were retained for audit.", "success")
    return redirect(url_for("tracker.members"))


def normalize_phone(raw):
    value = re.sub(r"[^0-9+]", "", str(raw or ""))
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    if value.startswith("+") and len(digits) >= 8:
        return "+" + digits
    return digits


def read_rows(upload):
    filename = upload.filename.lower()
    if filename.endswith(".csv"):
        content = upload.read().decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(content)))
    if filename.endswith(".xlsx"):
        workbook = load_workbook(upload, read_only=True, data_only=True)
        worksheet = workbook.active
        rows = worksheet.iter_rows(values_only=True)
        headers = [str(value or "").strip().lower() for value in next(rows, [])]
        return [dict(zip(headers, row)) for row in rows]
    raise ValueError("Upload a .csv or .xlsx file.")


def field(row, choices):
    normalized = {
        re.sub(r"[^a-z0-9]", "", str(key).lower()): value
        for key, value in row.items()
    }
    for key in choices:
        if key in normalized and normalized[key] is not None:
            return str(normalized[key]).strip()
    return ""


@tracker.route("/contacts/import/", methods=["POST"])
@admin_required
def import_contacts():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return Response("Upload a CSV or XLSX file.", status=400)
    try:
        rows = read_rows(upload)
    except (ValueError, BadZipFile, InvalidFileException, OSError) as error:
        flash(f"Could not read file: {error}", "error")
        return redirect(url_for("tracker.dashboard"))

    cleaned = []
    seen = set()
    for row in rows:
        phone = normalize_phone(
            field(row, ["phone", "mobile", "mobilenumber", "phonenumber", "number", "telephone"])
        )
        if not phone or phone in seen:
            continue
        seen.add(phone)
        cleaned.append(
            {
                "phone": phone,
                "name": field(row, ["name", "fullname", "contactname", "displayname"]),
                "group": field(row, ["group", "groupname", "sourcegroup"]),
            }
        )

    existing = set(
        db.session.scalars(
            select(Contact.phone).where(Contact.phone.in_([item["phone"] for item in cleaned]))
        ).all()
    )
    new_rows = [item for item in cleaned if item["phone"] not in existing]
    member_list = db.session.scalars(
        select(User)
        .where(User.is_committee_member.is_(True), User.is_active.is_(True))
        .order_by(User.id)
    ).all()
    if not member_list and new_rows:
        flash("Add at least one active committee member before importing contacts.", "error")
        return redirect(url_for("tracker.dashboard"))

    for index, item in enumerate(new_rows):
        member = member_list[index % len(member_list)]
        db.session.add(
            Contact(
                name=item["name"][:180],
                phone=item["phone"],
                source_group=item["group"][:180],
                assigned_to=member,
            )
        )
    db.session.add(
        AuditLog(
            actor=current_user,
            action="contacts_imported",
            details=(
                f"Rows read={len(rows)}, unique valid={len(cleaned)}, "
                f"created={len(new_rows)}, duplicates skipped={len(rows)-len(new_rows)}"
            ),
        )
    )
    db.session.commit()
    flash(
        f"Imported {len(new_rows)} new contacts. "
        f"{len(rows)-len(new_rows)} duplicates/invalid or already-existing entries were skipped.",
        "success",
    )
    return redirect(url_for("tracker.dashboard"))


@tracker.route("/contacts/<int:contact_id>/status/", methods=["POST"])
@login_required
def update_status(contact_id):
    contact = db.session.get(Contact, contact_id)
    if contact is None:
        abort(404)
    if not current_user.is_superuser and contact.assigned_to_id != current_user.id:
        abort(403)
    status = request.form.get("status")
    destination = request.form.get("destination", "")
    allowed_statuses = dict(Contact.STATUS_CHOICES)
    allowed_destinations = dict(Contact.DESTINATION_CHOICES)
    if status not in allowed_statuses:
        return Response("Invalid status", status=400)
    if status == "success" and destination not in allowed_destinations:
        return Response(
            "Choose Chennai, Kilpauk, or TYP for a successful contact.",
            status=400,
        )
    if status != "success":
        destination = ""
    previous = f"{contact.status}/{contact.destination}"
    contact.status = status
    contact.destination = destination
    contact.notes = request.form.get("notes", "")[:500]
    db.session.add(
        AuditLog(
            actor=current_user,
            contact=contact,
            action="status_updated",
            details=f"{previous} -> {status}/{destination}",
        )
    )
    db.session.commit()
    flash("Contact status updated.", "success")
    return redirect(url_for("tracker.dashboard"))


@tracker.route("/contacts/export.xlsx")
@admin_required
def export_excel():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "All Contacts"
    worksheet.append(
        [
            "Name",
            "Mobile",
            "Assigned Member",
            "Member Mobile",
            "Status",
            "Success Destination",
            "Source Group",
            "Created At",
            "Last Updated",
        ]
    )
    contacts = db.session.scalars(select(Contact).order_by(Contact.phone)).all()
    for contact in contacts:
        worksheet.append(
            [
                contact.name,
                contact.phone,
                contact.assigned_to.username if contact.assigned_to else "",
                contact.assigned_to.mobile if contact.assigned_to else "",
                contact.status_display,
                contact.destination_display if contact.destination else "",
                contact.source_group,
                contact.created_at.strftime("%Y-%m-%d %H:%M") if contact.created_at else "",
                contact.updated_at.strftime("%Y-%m-%d %H:%M") if contact.updated_at else "",
            ]
        )
    for column in worksheet.columns:
        letter = column[0].column_letter
        worksheet.column_dimensions[letter].width = min(
            max(max(len(str(cell.value or "")) for cell in column) + 2, 12),
            35,
        )
    audit_sheet = workbook.create_sheet("Audit Log")
    audit_sheet.append(["Timestamp", "Actor", "Action", "Contact Mobile", "Details"])
    logs = db.session.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc())
    ).all()
    for log in logs:
        audit_sheet.append(
            [
                log.created_at.strftime("%Y-%m-%d %H:%M"),
                log.actor.mobile if log.actor else "",
                log.action,
                log.contact.phone if log.contact else "",
                log.details,
            ]
        )
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="committee_contacts.xlsx",
    )


@tracker.route("/extension/import/", methods=["POST"])
@admin_required
def extension_import():
    try:
        data = json.loads(request.get_data(as_text=True))
        contacts = data.get("contacts", [])
        source = str(data.get("groupName", "WhatsApp group"))[:180]
    except (json.JSONDecodeError, AttributeError, TypeError):
        return Response("Invalid JSON", status=400)
    if not isinstance(contacts, list):
        return Response("Invalid contacts list", status=400)

    member_list = db.session.scalars(
        select(User)
        .where(User.is_committee_member.is_(True), User.is_active.is_(True))
        .order_by(User.id)
    ).all()
    if contacts and not member_list:
        return Response("Add active committee members first.", status=400)
    cleaned = []
    seen = set()
    for item in contacts:
        if not isinstance(item, dict):
            continue
        phone = normalize_phone(item.get("phone", ""))
        if phone and phone not in seen:
            exists = db.session.scalar(select(Contact.id).where(Contact.phone == phone))
            if exists is None:
                seen.add(phone)
                cleaned.append((str(item.get("name", ""))[:180], phone))
    for index, (name, phone) in enumerate(cleaned):
        db.session.add(
            Contact(
                name=name,
                phone=phone,
                assigned_to=member_list[index % len(member_list)],
                source_group=source,
            )
        )
    db.session.add(
        AuditLog(
            actor=current_user,
            action="whatsapp_extension_import",
            details=f"Group={source}; created={len(cleaned)}",
        )
    )
    db.session.commit()
    return jsonify(
        {"created": len(cleaned), "message": f"Imported {len(cleaned)} new contacts."}
    )
