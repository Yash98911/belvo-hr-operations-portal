from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Person(models.Model):
    class Status(models.TextChoices):
        ONBOARDING = "onboarding", "Onboarding"
        ACTIVE = "active", "Active"
        OFFBOARDING = "offboarding", "Offboarding"
        INACTIVE = "inactive", "Inactive"

    full_name = models.CharField(max_length=160)
    role_department = models.CharField(max_length=160)
    reporting_person = models.CharField(max_length=160, blank=True)
    contact_details = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ONBOARDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Onboarding(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        WAITING = "waiting", "Waiting"
        COMPLETED = "completed", "Completed"

    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="onboarding")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    assigned_hr_owner = models.CharField(max_length=160, blank=True)
    details_collected = models.BooleanField(default=False)
    documents_received = models.BooleanField(default=False)
    nda_issued_signed = models.BooleanField(default=False)
    joining_communication = models.BooleanField(default=False)
    access_requested = models.BooleanField(default=False)
    introduction_completed = models.BooleanField(default=False)
    onboarding_marked_complete = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Onboarding: {self.person.full_name}"


class Offboarding(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not Started"
        IN_PROGRESS = "in_progress", "In Progress"
        WAITING = "waiting", "Waiting"
        COMPLETED = "completed", "Completed"

    person = models.OneToOneField(Person, on_delete=models.PROTECT, related_name="offboarding")
    department = models.CharField(max_length=160)
    last_working_date = models.DateField()
    reason_category = models.CharField(max_length=120, blank=True)
    hr_owner = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOT_STARTED)
    due_date = models.DateField(null=True, blank=True)
    exit_communication = models.BooleanField(default=False)
    handover_received = models.BooleanField(default=False)
    pending_work_checked = models.BooleanField(default=False)
    records_updated = models.BooleanField(default=False)
    access_removal_requested = models.BooleanField(default=False)
    nda_documents_checked = models.BooleanField(default=False)
    exit_marked_complete = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_working_date", "person__full_name"]

    @property
    def checklist_completed_count(self):
        return sum(
            (
                self.exit_communication,
                self.handover_received,
                self.pending_work_checked,
                self.records_updated,
                self.access_removal_requested,
                self.nda_documents_checked,
                self.exit_marked_complete,
            )
        )

    def clean(self):
        super().clean()
        checklist = (
            self.exit_communication,
            self.handover_received,
            self.pending_work_checked,
            self.records_updated,
            self.access_removal_requested,
            self.nda_documents_checked,
            self.exit_marked_complete,
        )
        if self.status == self.Status.COMPLETED and not all(checklist):
            raise ValidationError({"status": "Complete every exit checklist item before marking offboarding completed."})

    def __str__(self):
        return f"Offboarding: {self.person.full_name}"


class WebsiteAsset(models.Model):
    class Status(models.TextChoices):
        PENDING_COLLECTION = "pending_collection", "Pending Collection"
        READY_TO_SHARE = "ready_to_share", "Ready to Share"
        SHARED_WITH_DEVELOPER = "shared_with_developer", "Shared with Developer"
        UPDATED = "updated", "Updated"
        VERIFIED = "verified", "Verified"

    section_name = models.CharField(max_length=180)
    current_asset_link = models.URLField(max_length=500, blank=True)
    replacement_asset_link = models.URLField(max_length=500, blank=True)
    responsible_person = models.CharField(max_length=160, blank=True)
    requested_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING_COLLECTION)
    last_updated = models.DateField(auto_now=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-requested_date", "section_name"]
        indexes = [models.Index(fields=["status", "requested_date"])]

    def clean(self):
        super().clean()
        for field_name in ("current_asset_link", "replacement_asset_link"):
            link = getattr(self, field_name)
            if link and not link.startswith("https://"):
                raise ValidationError({field_name: "Asset links must use HTTPS."})

    def __str__(self):
        return self.section_name


class LinkedInCheck(models.Model):
    class Status(models.TextChoices):
        NOT_YET_CHECKED = "not_yet_checked", "Not Yet Checked"
        DONE = "done", "Done"
        FOLLOW_UP_REQUIRED = "follow_up_required", "Follow-up Required"

    class ProfileStatus(models.TextChoices):
        NEEDS_REVIEW = "needs_review", "Needs Review"
        CURRENT = "current", "Current"
        UPDATE_REQUIRED = "update_required", "Update Required"
        NOT_APPLICABLE = "not_applicable", "Not Applicable"

    person = models.OneToOneField(Person, on_delete=models.PROTECT, related_name="linkedin_check")
    profile_url = models.URLField(max_length=500)
    department = models.CharField(max_length=160)
    assigned_reviewer = models.CharField(max_length=160, blank=True)
    last_checked_date = models.DateField(null=True, blank=True)
    profile_status = models.CharField(max_length=24, choices=ProfileStatus.choices, default=ProfileStatus.NEEDS_REVIEW)
    check_status = models.CharField(max_length=24, choices=Status.choices, default=Status.NOT_YET_CHECKED)
    feedback_action_required = models.CharField(max_length=240, blank=True)
    next_check_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_check_date", "person__full_name"]
        indexes = [models.Index(fields=["check_status", "next_check_date"])]

    def clean(self):
        super().clean()
        profile_host = urlsplit(self.profile_url).hostname if self.profile_url else None
        if self.profile_url and (
            not self.profile_url.lower().startswith("https://")
            or not profile_host
            or not (profile_host == "linkedin.com" or profile_host.endswith(".linkedin.com"))
        ):
            raise ValidationError({"profile_url": "Enter a valid HTTPS LinkedIn profile link."})
        if self.check_status == self.Status.DONE and not self.last_checked_date:
            raise ValidationError({"last_checked_date": "Enter the date this profile was checked."})

    def __str__(self):
        return f"LinkedIn check: {self.person.full_name}"


class FoundingTeamRequest(models.Model):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In Progress"
        WAITING = "waiting", "Waiting"
        COMPLETED = "completed", "Completed"

    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    requester = models.CharField(max_length=160)
    assigned_hr_owner = models.CharField(max_length=160, blank=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    follow_up_notes = models.TextField(blank=True)
    completion_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "-priority", "-created_at"]
        indexes = [models.Index(fields=["status", "due_date"])]

    def __str__(self):
        return self.title


class MeetingAgendaTemplate(models.Model):
    title = models.CharField(max_length=120, unique=True)
    agenda = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class DepartmentalMeeting(models.Model):
    department = models.CharField(max_length=160)
    date = models.DateField()
    time = models.TimeField()
    host = models.CharField(max_length=160)
    attendees = models.TextField(blank=True)
    agenda_template = models.ForeignKey(
        MeetingAgendaTemplate,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="meetings",
    )
    agenda = models.TextField(blank=True)
    meeting_location = models.CharField(max_length=240, blank=True)
    meeting_link = models.URLField(max_length=500, blank=True)
    meeting_notes = models.TextField(blank=True)
    participation_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-time"]
        indexes = [models.Index(fields=["date", "department"])]

    def clean(self):
        super().clean()
        if self.meeting_link and not self.meeting_link.startswith("https://"):
            raise ValidationError({"meeting_link": "Meeting links must use HTTPS."})

    def __str__(self):
        return f"{self.department} meeting · {self.date}"


class MeetingActionItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"

    meeting = models.ForeignKey(DepartmentalMeeting, on_delete=models.CASCADE, related_name="action_items")
    action_item = models.CharField(max_length=240)
    owner = models.CharField(max_length=160)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    completion_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "action_item"]
        indexes = [models.Index(fields=["status", "due_date"])]

    def __str__(self):
        return self.action_item


class LeaveEntry(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Declined"
        RECORDED = "recorded", "Recorded"

    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="leave_entries")
    department = models.CharField(max_length=160)
    leave_type = models.CharField(max_length=80)
    from_date = models.DateField()
    to_date = models.DateField()
    number_of_days = models.PositiveSmallIntegerField(default=1)
    reason = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_leave_entries")
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-from_date", "person__full_name"]

    def clean(self):
        super().clean()
        if self.from_date and self.to_date:
            if self.to_date < self.from_date:
                raise ValidationError({"to_date": "The end date must be on or after the start date."})
            self.number_of_days = (self.to_date - self.from_date).days + 1

    def __str__(self):
        return f"{self.person.full_name} · {self.from_date}"


class AttendanceEntry(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        LEAVE = "leave", "On leave"
        HOLIDAY = "holiday", "Holiday"

    class Arrangement(models.TextChoices):
        OFFICE = "office", "Office"
        REMOTE = "remote", "Remote"
        HYBRID = "hybrid", "Hybrid"

    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="attendance_entries")
    department = models.CharField(max_length=160)
    date = models.DateField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PRESENT)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    arrangement = models.CharField(max_length=16, choices=Arrangement.choices, blank=True)
    remarks = models.CharField(max_length=240, blank=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="updated_attendance_entries")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "person__full_name"]
        constraints = [
            models.UniqueConstraint(fields=["person", "date"], name="unique_attendance_person_date"),
        ]

    def __str__(self):
        return f"{self.person.full_name} · {self.date}"


class EmployeeDocument(models.Model):
    class Category(models.TextChoices):
        IDENTITY = "identity", "Identity details"
        EDUCATION = "education", "Education documents"
        JOINING = "joining", "Joining documents"
        CERTIFICATE = "certificate", "Certificates"
        OTHER = "other", "Other HR-approved records"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        RECEIVED = "received", "Received"

    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="documents")
    department = models.CharField(max_length=160)
    category = models.CharField(max_length=20, choices=Category.choices)
    drive_link = models.URLField(max_length=500, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.REQUESTED)
    date_received = models.DateField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["person__full_name", "category"]

    def __str__(self):
        return f"{self.person.full_name} · {self.get_category_display()}"


class NDARecord(models.Model):
    class Status(models.TextChoices):
        NOT_PREPARED = "not_prepared", "Not Prepared"
        TO_BE_SENT = "to_be_sent", "To Be Sent"
        SENT = "sent", "Sent"
        SIGNED = "signed", "Signed"
        PENDING_FOLLOW_UP = "pending_follow_up", "Pending Follow-up"
        NOT_APPLICABLE = "not_applicable", "Not Applicable"

    person_or_company = models.CharField(max_length=180)
    department_relationship = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NOT_PREPARED)
    sent_date = models.DateField(null=True, blank=True)
    signed_date = models.DateField(null=True, blank=True)
    drive_link = models.URLField(max_length=500, blank=True)
    responsible_hr_owner = models.CharField(max_length=160, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["person_or_company"]

    def __str__(self):
        return f"NDA · {self.person_or_company}"


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=20)
    record_type = models.CharField(max_length=40)
    record_id = models.PositiveIntegerField()
    summary = models.CharField(max_length=240)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}: {self.summary}"
