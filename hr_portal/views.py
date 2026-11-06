import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AttendanceEntryForm,
    DepartmentalMeetingForm,
    EmployeeDocumentForm,
    FoundingTeamRequestForm,
    LeaveEntryForm,
    LinkedInCheckForm,
    MeetingActionItemForm,
    MeetingAgendaTemplateForm,
    NDARecordForm,
    OffboardingForm,
    OnboardingForm,
    PersonForm,
    WebsiteAssetForm,
)
from .models import (
    AttendanceEntry,
    AuditEvent,
    DepartmentalMeeting,
    EmployeeDocument,
    FoundingTeamRequest,
    LeaveEntry,
    LinkedInCheck,
    MeetingActionItem,
    MeetingAgendaTemplate,
    NDARecord,
    Offboarding,
    Onboarding,
    Person,
    WebsiteAsset,
)


def _filtered_records(request, queryset, search_fields, status_field=None):
    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    if query:
        search = Q()
        for field in search_fields:
            search |= Q(**{f"{field}__icontains": query})
        queryset = queryset.filter(search)
    if status and status_field:
        queryset = queryset.filter(**{status_field: status})
    page = Paginator(queryset, 20).get_page(request.GET.get("page"))
    return page, query, status


def _apply_month_filter(request, queryset, field_name):
    month = request.GET.get("month", "").strip()
    if len(month) == 7 and month[4] == "-":
        year, month_number = month.split("-", 1)
        if year.isdigit() and month_number.isdigit() and 1 <= int(month_number) <= 12:
            queryset = queryset.filter(**{f"{field_name}__year": int(year), f"{field_name}__month": int(month_number)})
    else:
        month = ""
    return queryset, month


def _form_changes(form):
    sensitive_fields = {
        "full_name",
        "contact_details",
        "notes",
        "remarks",
        "reason",
        "drive_link",
        "agenda",
        "attendees",
        "meeting_notes",
        "participation_notes",
        "feedback_action_required",
        "description",
        "follow_up_notes",
        "completion_notes",
    }
    changes = {}
    for field_name in form.changed_data:
        if field_name in sensitive_fields:
            changes[form.fields[field_name].label] = "Updated"
            continue
        before = form.initial.get(field_name)
        after = form.cleaned_data.get(field_name)
        changes[form.fields[field_name].label] = {
            "before": str(before) if before is not None else "",
            "after": str(after) if after is not None else "",
        }
    return changes


def _form_page(request, form, title, back_url, save_label):
    context = {"form": form, "title": title, "back_url": back_url, "save_label": save_label}
    context["offboarding_form"] = isinstance(form, OffboardingForm)
    if isinstance(form, dict):
        context.update(form)
    return render(request, "hr_portal/form.html", context)


@login_required
def dashboard(request):
    today = timezone.localdate()
    pending_onboardings = Onboarding.objects.exclude(status=Onboarding.Status.COMPLETED).select_related("person")
    pending_leave = LeaveEntry.objects.filter(status=LeaveEntry.Status.PENDING).select_related("person")
    upcoming_starts = Person.objects.filter(
        status=Person.Status.ONBOARDING,
        start_date__gte=today,
        start_date__lte=today + timedelta(days=14),
    ).order_by("start_date")[:5]
    attendance_exceptions = AttendanceEntry.objects.filter(
        date=today,
        status__in=[AttendanceEntry.Status.ABSENT, AttendanceEntry.Status.LATE],
    ).select_related("person")
    pending_offboardings = Offboarding.objects.exclude(status=Offboarding.Status.COMPLETED).select_related("person")
    overdue_offboardings = pending_offboardings.filter(due_date__lt=today)
    pending_requests = FoundingTeamRequest.objects.exclude(status=FoundingTeamRequest.Status.COMPLETED)
    today_meetings = DepartmentalMeeting.objects.filter(date=today)
    open_assets = WebsiteAsset.objects.exclude(status=WebsiteAsset.Status.VERIFIED)
    linkedin_followups = LinkedInCheck.objects.filter(
        Q(check_status=LinkedInCheck.Status.FOLLOW_UP_REQUIRED)
        | Q(next_check_date__lte=today),
    ).exclude(check_status=LinkedInCheck.Status.DONE)
    pending_meeting_actions = MeetingActionItem.objects.filter(status__in=[
        MeetingActionItem.Status.PENDING,
        MeetingActionItem.Status.IN_PROGRESS,
    ])

    return render(
        request,
        "hr_portal/dashboard.html",
        {
            "active_people": Person.objects.filter(status=Person.Status.ACTIVE).count(),
            "onboarding_count": pending_onboardings.count(),
            "pending_leave_count": pending_leave.count(),
            "attendance_exception_count": attendance_exceptions.count(),
            "pending_document_count": EmployeeDocument.objects.filter(status=EmployeeDocument.Status.REQUESTED).count(),
            "pending_nda_count": NDARecord.objects.exclude(
                status__in=[NDARecord.Status.SIGNED, NDARecord.Status.NOT_APPLICABLE]
            ).count(),
            "offboarding_count": pending_offboardings.count(),
            "overdue_offboarding_count": overdue_offboardings.count(),
            "pending_request_count": pending_requests.count(),
            "overdue_request_count": pending_requests.filter(due_date__lt=today).count(),
            "today_meeting_count": today_meetings.count(),
            "pending_meeting_action_count": pending_meeting_actions.count(),
            "open_asset_count": open_assets.count(),
            "linkedin_followup_count": linkedin_followups.count(),
            "pending_onboardings": pending_onboardings[:5],
            "pending_leave": pending_leave[:5],
            "upcoming_starts": upcoming_starts,
            "attendance_exceptions": attendance_exceptions[:5],
            "pending_offboardings": pending_offboardings.order_by("due_date", "last_working_date")[:5],
            "pending_requests": pending_requests.order_by("due_date", "-priority")[:5],
            "today_meetings": today_meetings.order_by("time")[:5],
            "pending_meeting_actions": pending_meeting_actions.select_related("meeting").order_by("due_date")[:5],
            "open_assets": open_assets.order_by("requested_date")[:5],
            "today": today,
        },
    )


@login_required
def onboarding_list(request):
    records, query, status = _filtered_records(
        request,
        Onboarding.objects.select_related("person"),
        ["person__full_name", "person__role_department", "assigned_hr_owner"],
        "status",
    )
    return render(
        request,
        "hr_portal/onboarding_list.html",
        {"records": records, "query": query, "status": status, "status_choices": Onboarding.Status.choices},
    )


@login_required
@transaction.atomic
def onboarding_create(request):
    person_form = PersonForm(request.POST or None, prefix="person")
    onboarding_form = OnboardingForm(request.POST or None, prefix="onboarding")
    if request.method == "POST":
        person_valid = person_form.is_valid()
        onboarding_valid = onboarding_form.is_valid()
        if person_valid and onboarding_valid:
            person = person_form.save()
            onboarding = onboarding_form.save(commit=False)
            onboarding.person = person
            onboarding.save()
            _audit(request, "created", onboarding, f"Onboarding created for {person.full_name}")
            messages.success(request, f"Onboarding record created for {person.full_name}.")
            return redirect("onboarding-list")
    return _form_page(
        request,
        {"person_form": person_form, "onboarding_form": onboarding_form},
        "Add onboarding record",
        "onboarding-list",
        "Create record",
    )


@login_required
@transaction.atomic
def onboarding_edit(request, pk):
    onboarding = get_object_or_404(Onboarding.objects.select_related("person"), pk=pk)
    person_form = PersonForm(request.POST or None, instance=onboarding.person, prefix="person")
    onboarding_form = OnboardingForm(request.POST or None, instance=onboarding, prefix="onboarding")
    if request.method == "POST":
        person_valid = person_form.is_valid()
        onboarding_valid = onboarding_form.is_valid()
        if person_valid and onboarding_valid:
            changes = {
                "person": _form_changes(person_form),
                "onboarding": _form_changes(onboarding_form),
            }
            person = person_form.save()
            onboarding_form.save()
            _audit(request, "updated", onboarding, f"Onboarding updated for {person.full_name}", changes)
            messages.success(request, f"Onboarding record updated for {person.full_name}.")
            return redirect("onboarding-list")
    return _form_page(
        request,
        {"person_form": person_form, "onboarding_form": onboarding_form},
        f"Edit onboarding · {onboarding.person.full_name}",
        "onboarding-list",
        "Save changes",
    )


@login_required
def offboarding_list(request):
    records, query, status = _filtered_records(
        request,
        Offboarding.objects.select_related("person"),
        ["person__full_name", "department", "reason_category", "hr_owner"],
        "status",
    )
    return render(
        request,
        "hr_portal/offboarding_list.html",
        {
            "records": records,
            "query": query,
            "status": status,
            "status_choices": Offboarding.Status.choices,
            "today": timezone.localdate(),
        },
    )


@login_required
@transaction.atomic
def offboarding_create(request):
    form = OffboardingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.full_clean()
        record.save()
        person = record.person
        person.status = Person.Status.INACTIVE if record.status == Offboarding.Status.COMPLETED else Person.Status.OFFBOARDING
        person.save(update_fields=["status", "updated_at"])
        _audit(request, "created", record, f"Offboarding created for {person.full_name}")
        messages.success(request, f"Offboarding record created for {person.full_name}.")
        return redirect("offboarding-list")
    return _form_page(request, form, "Add offboarding record", "offboarding-list", "Create record")


@login_required
@transaction.atomic
def offboarding_edit(request, pk):
    record = get_object_or_404(Offboarding.objects.select_related("person"), pk=pk)
    form = OffboardingForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        record = form.save(commit=False)
        record.full_clean()
        record.save()
        person = record.person
        person.status = Person.Status.INACTIVE if record.status == Offboarding.Status.COMPLETED else Person.Status.OFFBOARDING
        person.save(update_fields=["status", "updated_at"])
        _audit(request, "updated", record, f"Offboarding updated for {person.full_name}", changes)
        messages.success(request, f"Offboarding record updated for {person.full_name}.")
        return redirect("offboarding-list")
    return _form_page(
        request,
        form,
        f"Edit offboarding · {record.person.full_name}",
        "offboarding-list",
        "Save changes",
    )


@login_required
def leave_list(request):
    queryset = LeaveEntry.objects.select_related("person", "recorded_by")
    queryset, month = _apply_month_filter(request, queryset, "from_date")
    records, query, status = _filtered_records(
        request,
        queryset,
        ["person__full_name", "department", "leave_type"],
        "status",
    )
    return render(
        request,
        "hr_portal/leave_list.html",
        {"records": records, "query": query, "status": status, "month": month, "status_choices": LeaveEntry.Status.choices},
    )


@login_required
@transaction.atomic
def leave_create(request):
    form = LeaveEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.recorded_by = request.user
        entry.full_clean()
        entry.save()
        _audit(request, "created", entry, f"Leave recorded for {entry.person.full_name}")
        messages.success(request, "Leave entry created.")
        return redirect("leave-list")
    return _form_page(request, form, "Add leave entry", "leave-list", "Create entry")


@login_required
@transaction.atomic
def leave_edit(request, pk):
    entry = get_object_or_404(LeaveEntry.objects.select_related("person"), pk=pk)
    form = LeaveEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        entry = form.save(commit=False)
        entry.recorded_by = request.user
        entry.full_clean()
        entry.save()
        _audit(request, "updated", entry, f"Leave updated for {entry.person.full_name}", changes)
        messages.success(request, "Leave entry updated.")
        return redirect("leave-list")
    return _form_page(request, form, f"Edit leave · {entry.person.full_name}", "leave-list", "Save changes")


@login_required
def attendance_list(request):
    queryset = AttendanceEntry.objects.select_related("person", "updated_by")
    queryset, month = _apply_month_filter(request, queryset, "date")
    records, query, status = _filtered_records(
        request,
        queryset,
        ["person__full_name", "department", "remarks"],
        "status",
    )
    return render(
        request,
        "hr_portal/attendance_list.html",
        {"records": records, "query": query, "status": status, "month": month, "status_choices": AttendanceEntry.Status.choices},
    )


@login_required
@transaction.atomic
def attendance_create(request):
    form = AttendanceEntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        entry = form.save(commit=False)
        entry.updated_by = request.user
        entry.full_clean()
        entry.save()
        _audit(request, "created", entry, f"Attendance recorded for {entry.person.full_name} on {entry.date}")
        messages.success(request, "Attendance entry created.")
        return redirect("attendance-list")
    return _form_page(request, form, "Add attendance entry", "attendance-list", "Create entry")


@login_required
@transaction.atomic
def attendance_edit(request, pk):
    entry = get_object_or_404(AttendanceEntry.objects.select_related("person"), pk=pk)
    form = AttendanceEntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        entry = form.save(commit=False)
        entry.updated_by = request.user
        entry.full_clean()
        entry.save()
        _audit(request, "updated", entry, f"Attendance updated for {entry.person.full_name} on {entry.date}", changes)
        messages.success(request, "Attendance entry updated.")
        return redirect("attendance-list")
    return _form_page(request, form, f"Edit attendance · {entry.person.full_name}", "attendance-list", "Save changes")


@login_required
def onboarding_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="belvo-onboarding-register.csv"'
    writer = csv.writer(response)
    checklist = [
        ("Details collected", "details_collected"),
        ("Documents received", "documents_received"),
        ("NDA issued/signed", "nda_issued_signed"),
        ("Joining communication", "joining_communication"),
        ("Access requested", "access_requested"),
        ("Introduction completed", "introduction_completed"),
        ("Onboarding marked complete", "onboarding_marked_complete"),
    ]
    writer.writerow(
        ["Person", "Role / department", "Reporting person", "Start date", "Status", "HR owner", "Due date"]
        + [label for label, _ in checklist]
    )
    for record in Onboarding.objects.select_related("person"):
        writer.writerow(
            [
                record.person.full_name,
                record.person.role_department,
                record.person.reporting_person,
                record.person.start_date or "",
                record.get_status_display(),
                record.assigned_hr_owner,
                record.due_date or "",
            ]
            + ["Yes" if getattr(record, field) else "No" for _, field in checklist]
        )
    return response


@login_required
def offboarding_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="belvo-offboarding-register.csv"'
    writer = csv.writer(response)
    checklist = [
        ("Exit communication", "exit_communication"),
        ("Handover received", "handover_received"),
        ("Pending work checked", "pending_work_checked"),
        ("Records updated", "records_updated"),
        ("Access removal requested", "access_removal_requested"),
        ("NDA/documents checked", "nda_documents_checked"),
        ("Exit marked complete", "exit_marked_complete"),
    ]
    writer.writerow(["Person", "Department", "Last working date", "Reason/category", "HR owner", "Status", "Due date"] + [label for label, _ in checklist])
    for record in Offboarding.objects.select_related("person"):
        writer.writerow(
            [
                record.person.full_name,
                record.department,
                record.last_working_date,
                record.reason_category,
                record.hr_owner,
                record.get_status_display(),
                record.due_date or "",
            ]
            + ["Yes" if getattr(record, field) else "No" for _, field in checklist]
        )
    return response


@login_required
def leave_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="belvo-leave-register.csv"'
    writer = csv.writer(response)
    writer.writerow(["Person", "Department", "Leave type", "From", "To", "Days", "Reason", "Status", "Recorded by", "Remarks"])
    for entry in LeaveEntry.objects.select_related("person", "recorded_by"):
        writer.writerow(
            [
                entry.person.full_name,
                entry.department,
                entry.leave_type,
                entry.from_date,
                entry.to_date,
                entry.number_of_days,
                entry.reason,
                entry.get_status_display(),
                entry.recorded_by.get_username(),
                entry.remarks,
            ]
        )
    return response


@login_required
def attendance_export(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="belvo-attendance-register.csv"'
    writer = csv.writer(response)
    writer.writerow(["Person", "Department", "Date", "Status", "Check-in", "Check-out", "Arrangement", "Remarks", "Updated by"])
    for entry in AttendanceEntry.objects.select_related("person", "updated_by"):
        writer.writerow(
            [
                entry.person.full_name,
                entry.department,
                entry.date,
                entry.get_status_display(),
                entry.check_in or "",
                entry.check_out or "",
                entry.get_arrangement_display() if entry.arrangement else "",
                entry.remarks,
                entry.updated_by.get_username(),
            ]
        )
    return response


@login_required
def document_list(request):
    records, query, status = _filtered_records(
        request,
        EmployeeDocument.objects.select_related("person"),
        ["person__full_name", "department", "category", "remarks"],
        "status",
    )
    return render(
        request,
        "hr_portal/document_list.html",
        {"records": records, "query": query, "status": status, "status_choices": EmployeeDocument.Status.choices},
    )


@login_required
def document_create(request):
    form = EmployeeDocumentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        _audit(request, "created", record, f"Document register entry created for {record.person.full_name}")
        messages.success(request, "Document register entry created.")
        return redirect("document-list")
    return _form_page(request, form, "Add document record", "document-list", "Create record")


@login_required
def document_edit(request, pk):
    record = get_object_or_404(EmployeeDocument.objects.select_related("person"), pk=pk)
    form = EmployeeDocumentForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        record = form.save()
        _audit(request, "updated", record, f"Document register entry updated for {record.person.full_name}", changes)
        messages.success(request, "Document register entry updated.")
        return redirect("document-list")
    return _form_page(request, form, f"Edit document · {record.person.full_name}", "document-list", "Save changes")


@login_required
def nda_list(request):
    records, query, status = _filtered_records(
        request,
        NDARecord.objects.all(),
        ["person_or_company", "department_relationship", "responsible_hr_owner"],
        "status",
    )
    return render(
        request,
        "hr_portal/nda_list.html",
        {
            "records": records,
            "query": query,
            "status": status,
            "status_choices": NDARecord.Status.choices,
            "today": timezone.localdate(),
        },
    )


@login_required
def nda_create(request):
    form = NDARecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        _audit(request, "created", record, f"NDA register entry created for {record.person_or_company}")
        messages.success(request, "NDA register entry created.")
        return redirect("nda-list")
    return _form_page(request, form, "Add NDA record", "nda-list", "Create record")


@login_required
def nda_edit(request, pk):
    record = get_object_or_404(NDARecord, pk=pk)
    form = NDARecordForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        record = form.save()
        _audit(request, "updated", record, f"NDA register entry updated for {record.person_or_company}", changes)
        messages.success(request, "NDA register entry updated.")
        return redirect("nda-list")
    return _form_page(request, form, f"Edit NDA · {record.person_or_company}", "nda-list", "Save changes")


@login_required
def website_asset_list(request):
    records, query, status = _filtered_records(
        request,
        WebsiteAsset.objects.all(),
        ["section_name", "responsible_person", "notes"],
        "status",
    )
    return render(
        request,
        "hr_portal/website_asset_list.html",
        {"records": records, "query": query, "status": status, "status_choices": WebsiteAsset.Status.choices},
    )


@login_required
def website_asset_create(request):
    form = WebsiteAssetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        _audit(request, "created", record, f"Website asset tracker entry created for {record.section_name}")
        messages.success(request, "Website asset tracker entry created.")
        return redirect("website-asset-list")
    return _form_page(request, form, "Add website asset", "website-asset-list", "Create record")


@login_required
def website_asset_edit(request, pk):
    record = get_object_or_404(WebsiteAsset, pk=pk)
    form = WebsiteAssetForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        record = form.save()
        _audit(request, "updated", record, f"Website asset tracker entry updated for {record.section_name}", changes)
        messages.success(request, "Website asset tracker entry updated.")
        return redirect("website-asset-list")
    return _form_page(request, form, f"Edit asset · {record.section_name}", "website-asset-list", "Save changes")


@login_required
def linkedin_list(request):
    records, query, status = _filtered_records(
        request,
        LinkedInCheck.objects.select_related("person"),
        ["person__full_name", "department", "assigned_reviewer", "feedback_action_required"],
        "check_status",
    )
    return render(
        request,
        "hr_portal/linkedin_list.html",
        {
            "records": records,
            "query": query,
            "status": status,
            "status_choices": LinkedInCheck.Status.choices,
            "today": timezone.localdate(),
        },
    )


@login_required
def linkedin_create(request):
    form = LinkedInCheckForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        _audit(request, "created", record, f"LinkedIn tracker created for {record.person.full_name}")
        messages.success(request, "LinkedIn tracker record created.")
        return redirect("linkedin-list")
    return _form_page(request, form, "Add LinkedIn check", "linkedin-list", "Create record")


@login_required
def linkedin_edit(request, pk):
    record = get_object_or_404(LinkedInCheck.objects.select_related("person"), pk=pk)
    form = LinkedInCheckForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        record = form.save()
        _audit(request, "updated", record, f"LinkedIn tracker updated for {record.person.full_name}", changes)
        messages.success(request, "LinkedIn tracker record updated.")
        return redirect("linkedin-list")
    return _form_page(request, form, f"Edit LinkedIn check · {record.person.full_name}", "linkedin-list", "Save changes")


@login_required
def founding_request_list(request):
    records, query, status = _filtered_records(
        request,
        FoundingTeamRequest.objects.all(),
        ["title", "description", "requester", "assigned_hr_owner"],
        "status",
    )
    return render(
        request,
        "hr_portal/founding_request_list.html",
        {
            "records": records,
            "query": query,
            "status": status,
            "status_choices": FoundingTeamRequest.Status.choices,
            "today": timezone.localdate(),
        },
    )


@login_required
def founding_request_create(request):
    form = FoundingTeamRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        _audit(request, "created", record, f"Founding team request created: {record.title}")
        messages.success(request, "Founding team request created.")
        return redirect("founding-request-list")
    return _form_page(request, form, "Add founding team request", "founding-request-list", "Create request")


@login_required
def founding_request_edit(request, pk):
    record = get_object_or_404(FoundingTeamRequest, pk=pk)
    form = FoundingTeamRequestForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        record = form.save()
        _audit(request, "updated", record, f"Founding team request updated: {record.title}", changes)
        messages.success(request, "Founding team request updated.")
        return redirect("founding-request-list")
    return _form_page(request, form, f"Edit request · {record.title}", "founding-request-list", "Save changes")


@login_required
def meeting_list(request):
    queryset = DepartmentalMeeting.objects.all()
    queryset, month = _apply_month_filter(request, queryset, "date")
    records, query, _ = _filtered_records(
        request,
        queryset,
        ["department", "host", "attendees", "agenda"],
    )
    return render(
        request,
        "hr_portal/meeting_list.html",
        {"records": records, "query": query, "month": month, "today": timezone.localdate()},
    )


@login_required
def meeting_create(request):
    form = DepartmentalMeetingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        meeting = form.save()
        _audit(request, "created", meeting, f"Department meeting created for {meeting.department} on {meeting.date}")
        messages.success(request, "Department meeting created.")
        return redirect("meeting-detail", pk=meeting.pk)
    return _form_page(request, form, "Schedule department meeting", "meeting-list", "Create meeting")


@login_required
def meeting_detail(request, pk):
    meeting = get_object_or_404(DepartmentalMeeting.objects.select_related("agenda_template"), pk=pk)
    action_form = MeetingActionItemForm()
    if request.method == "POST":
        action_form = MeetingActionItemForm(request.POST)
        if action_form.is_valid():
            action_item = action_form.save(commit=False)
            action_item.meeting = meeting
            action_item.save()
            _audit(request, "created", action_item, f"Meeting action item created for {meeting.department}")
            messages.success(request, "Meeting action item added.")
            return redirect("meeting-detail", pk=meeting.pk)
    return render(
        request,
        "hr_portal/meeting_detail.html",
        {
            "meeting": meeting,
            "action_items": meeting.action_items.all(),
            "action_form": action_form,
            "today": timezone.localdate(),
        },
    )


@login_required
def meeting_edit(request, pk):
    meeting = get_object_or_404(DepartmentalMeeting, pk=pk)
    form = DepartmentalMeetingForm(request.POST or None, instance=meeting)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        meeting = form.save()
        _audit(request, "updated", meeting, f"Department meeting updated for {meeting.department} on {meeting.date}", changes)
        messages.success(request, "Department meeting updated.")
        return redirect("meeting-detail", pk=meeting.pk)
    return _form_page(request, form, f"Edit meeting · {meeting.department}", "meeting-list", "Save changes")


@login_required
def meeting_action_edit(request, pk, action_pk):
    meeting = get_object_or_404(DepartmentalMeeting, pk=pk)
    action_item = get_object_or_404(MeetingActionItem, pk=action_pk, meeting=meeting)
    form = MeetingActionItemForm(request.POST or None, instance=action_item)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        action_item = form.save()
        _audit(request, "updated", action_item, f"Meeting action item updated for {meeting.department}", changes)
        messages.success(request, "Meeting action item updated.")
        return redirect("meeting-detail", pk=meeting.pk)
    return _form_page(
        request,
        form,
        f"Edit action item · {meeting.department}",
        "meeting-list",
        "Save changes",
    )


@login_required
def agenda_template_list(request):
    return render(
        request,
        "hr_portal/agenda_template_list.html",
        {"records": MeetingAgendaTemplate.objects.all()},
    )


@login_required
def agenda_template_create(request):
    form = MeetingAgendaTemplateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        record = form.save()
        _audit(request, "created", record, f"Meeting agenda template created: {record.title}")
        messages.success(request, "Meeting agenda template created.")
        return redirect("agenda-template-list")
    return _form_page(request, form, "Add agenda template", "agenda-template-list", "Create template")


@login_required
def agenda_template_edit(request, pk):
    record = get_object_or_404(MeetingAgendaTemplate, pk=pk)
    form = MeetingAgendaTemplateForm(request.POST or None, instance=record)
    if request.method == "POST" and form.is_valid():
        changes = _form_changes(form)
        record = form.save()
        _audit(request, "updated", record, f"Meeting agenda template updated: {record.title}", changes)
        messages.success(request, "Meeting agenda template updated.")
        return redirect("agenda-template-list")
    return _form_page(request, form, f"Edit agenda template · {record.title}", "agenda-template-list", "Save changes")


def _audit(request, action, record, summary, changes=None):
    AuditEvent.objects.create(
        actor=request.user,
        action=action,
        record_type=record._meta.label,
        record_id=record.pk,
        summary=summary,
        changes=changes or {},
    )
