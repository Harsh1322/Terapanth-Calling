import csv, io, json, re
from collections import defaultdict
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from openpyxl import Workbook, load_workbook
from .models import User, Contact, AuditLog
from .forms import MobileLoginForm, MemberForm

def is_admin(user):
    return user.is_authenticated and user.is_superuser

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = MobileLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        mobile = re.sub(r"\D", "", form.cleaned_data["mobile"])
        admin_mobile = re.sub(r"\D", "", settings.ADMIN_MOBILE)
        admin = User.objects.filter(mobile=mobile, is_superuser=True, is_active=True).first()
        if admin and mobile == admin_mobile:
            login(request, admin)
            return redirect("dashboard")
        if not form.cleaned_data["password"]:
            form.add_error("password", "Enter your password to sign in as a committee member.")
        else:
            user = authenticate(request, username=mobile, password=form.cleaned_data["password"])
            if user is None:
                form.add_error(None, "Invalid mobile number or password.")
            else:
                login(request, user)
                return redirect("dashboard")
    return render(request, "login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def dashboard(request):
    contacts = Contact.objects.select_related("assigned_to").order_by("name", "phone")
    if not request.user.is_superuser:
        contacts = contacts.filter(assigned_to=request.user)
    stats = {
        "total": contacts.count(),
        "pending": contacts.filter(status="pending").count(),
        "success": contacts.filter(status="success").count(),
        "no_answer": contacts.filter(status="no_answer").count(),
        "invalid": contacts.filter(status="invalid").count(),
        "follow_up": contacts.filter(status="follow_up").count(),
    }
    members = User.objects.filter(is_committee_member=True, is_active=True).order_by("username")
    if request.user.is_superuser:
        member_stats = []
        for member in members:
            qs = Contact.objects.filter(assigned_to=member)
            member_stats.append({"member": member, "total": qs.count(), "success": qs.filter(status="success").count(),
                "pending": qs.filter(status__in=["pending","follow_up","no_answer"]).count(), "invalid": qs.filter(status="invalid").count()})
    else:
        member_stats = []
    return render(request, "dashboard.html", {"contacts": contacts[:500], "stats": stats, "member_stats": member_stats})

@login_required
@user_passes_test(is_admin)
def members(request):
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            mobile = re.sub(r"\D", "", form.cleaned_data["mobile"])
            if User.objects.filter(mobile=mobile).exists():
                messages.error(request, "A user with that mobile number already exists.")
            else:
                user = User.objects.create_user(username=form.cleaned_data["display_name"], mobile=mobile,
                    password=form.cleaned_data["password"], is_committee_member=True)
                AuditLog.objects.create(actor=request.user, action="member_added", details=f"Added member {mobile}")
                messages.success(request, f"Member {mobile} created.")
                return redirect("members")
    else:
        form = MemberForm()
    return render(request, "members.html", {"form": form, "members": User.objects.filter(is_committee_member=True).order_by("username")})

@login_required
@user_passes_test(is_admin)
@require_POST
def delete_member(request, user_id):
    user = get_object_or_404(User, id=user_id, is_committee_member=True)
    mobile = user.mobile
    user.is_active = False
    user.save(update_fields=["is_active"])
    AuditLog.objects.create(actor=request.user, action="member_deactivated", details=f"Deactivated {mobile}; contact ownership retained")
    messages.success(request, "Member deactivated. Existing assignments were retained for audit.")
    return redirect("members")

def normalize_phone(raw):
    s = re.sub(r"[^0-9+]", "", str(raw or ""))
    digits = re.sub(r"\D", "", s)
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    if s.startswith("+") and len(digits) >= 8:
        return "+" + digits
    return digits

def read_rows(upload):
    name = upload.name.lower()
    if name.endswith(".csv"):
        content = upload.read().decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(content)))
    if name.endswith(".xlsx"):
        wb = load_workbook(upload, read_only=True, data_only=True)
        ws = wb.active
        rows = ws.iter_rows(values_only=True)
        headers = [str(v or "").strip().lower() for v in next(rows, [])]
        return [dict(zip(headers, row)) for row in rows]
    raise ValueError("Upload a .csv or .xlsx file.")

def field(row, choices):
    normalized = {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k,v in row.items()}
    for key in choices:
        if key in normalized and normalized[key] is not None:
            return str(normalized[key]).strip()
    return ""

@login_required
@user_passes_test(is_admin)
def import_contacts(request):
    if request.method != "POST" or "file" not in request.FILES:
        return HttpResponseBadRequest("Upload a CSV or XLSX file.")
    try:
        rows = read_rows(request.FILES["file"])
    except Exception as exc:
        messages.error(request, f"Could not read file: {exc}")
        return redirect("dashboard")
    cleaned, seen = [], set()
    for row in rows:
        phone = normalize_phone(field(row, ["phone","mobile","mobilenumber","phonenumber","number","telephone"]))
        if not phone or phone in seen:
            continue
        seen.add(phone)
        cleaned.append({"phone": phone, "name": field(row, ["name","fullname","contactname","displayname"]),
                        "group": field(row, ["group","groupname","sourcegroup"])})
    existing = set(Contact.objects.filter(phone__in=[x["phone"] for x in cleaned]).values_list("phone", flat=True))
    new_rows = [x for x in cleaned if x["phone"] not in existing]
    members = list(User.objects.filter(is_committee_member=True, is_active=True).order_by("id"))
    if not members and new_rows:
        messages.error(request, "Add at least one active committee member before importing contacts.")
        return redirect("dashboard")
    counts = defaultdict(int)
    created = 0
    with transaction.atomic():
        for i, item in enumerate(new_rows):
            member = members[i % len(members)]
            Contact.objects.create(name=item["name"][:180], phone=item["phone"], source_group=item["group"][:180], assigned_to=member)
            counts[member.id] += 1
            created += 1
        AuditLog.objects.create(actor=request.user, action="contacts_imported", details=f"Rows read={len(rows)}, unique valid={len(cleaned)}, created={created}, duplicates skipped={len(rows)-created}")
    messages.success(request, f"Imported {created} new contacts. {len(rows)-created} duplicates/invalid or already-existing entries were skipped.")
    return redirect("dashboard")

@login_required
@require_POST
def update_status(request, contact_id):
    contact = get_object_or_404(Contact, id=contact_id)
    if not request.user.is_superuser and contact.assigned_to_id != request.user.id:
        return HttpResponse("Forbidden", status=403)
    status = request.POST.get("status")
    destination = request.POST.get("destination", "")
    allowed = dict(Contact.STATUS_CHOICES)
    if status not in allowed:
        return HttpResponseBadRequest("Invalid status")
    if status == "success" and destination not in dict(Contact.DESTINATION_CHOICES):
        return HttpResponseBadRequest("Choose Chennai, Kilpauk, or TYP for a successful contact.")
    if status != "success":
        destination = ""
    old = f"{contact.status}/{contact.destination}"
    contact.status, contact.destination = status, destination
    contact.notes = request.POST.get("notes", "")[:500]
    contact.save()
    AuditLog.objects.create(actor=request.user, contact=contact, action="status_updated", details=f"{old} -> {status}/{destination}")
    messages.success(request, "Contact status updated.")
    return redirect("dashboard")

@login_required
@user_passes_test(is_admin)
def export_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "All Contacts"
    ws.append(["Name","Mobile","Assigned Member","Member Mobile","Status","Success Destination","Source Group","Created At","Last Updated"])
    for c in Contact.objects.select_related("assigned_to").order_by("phone"):
        ws.append([c.name, c.phone, c.assigned_to.username if c.assigned_to else "", c.assigned_to.mobile if c.assigned_to else "",
            c.get_status_display(), c.get_destination_display() if c.destination else "", c.source_group,
            c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "", c.updated_at.strftime("%Y-%m-%d %H:%M") if c.updated_at else ""])
    for col in ws.columns:
        letter = col[0].column_letter
        ws.column_dimensions[letter].width = min(max(max(len(str(cell.value or "")) for cell in col)+2, 12), 35)
    audit = wb.create_sheet("Audit Log")
    audit.append(["Timestamp","Actor","Action","Contact Mobile","Details"])
    for log in AuditLog.objects.select_related("actor","contact").order_by("-created_at"):
        audit.append([log.created_at.strftime("%Y-%m-%d %H:%M"), log.actor.mobile if log.actor else "", log.action,
                      log.contact.phone if log.contact else "", log.details])
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="committee_contacts.xlsx"'
    wb.save(response)
    return response

@login_required
@user_passes_test(is_admin)
@require_POST
def extension_import(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        contacts = data.get("contacts", [])
        source = str(data.get("groupName", "WhatsApp group"))[:180]
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")
    members = list(User.objects.filter(is_committee_member=True, is_active=True).order_by("id"))
    if contacts and not members:
        return HttpResponseBadRequest("Add active committee members first.")
    cleaned, seen = [], set()
    for item in contacts:
        phone = normalize_phone(item.get("phone", ""))
        if phone and phone not in seen and not Contact.objects.filter(phone=phone).exists():
            seen.add(phone)
            cleaned.append((str(item.get("name",""))[:180], phone))
    with transaction.atomic():
        for i, (name, phone) in enumerate(cleaned):
            Contact.objects.create(name=name, phone=phone, assigned_to=members[i % len(members)], source_group=source)
        AuditLog.objects.create(actor=request.user, action="whatsapp_extension_import", details=f"Group={source}; created={len(cleaned)}")
    return JsonResponse({"created": len(cleaned), "message": f"Imported {len(cleaned)} new contacts."})
