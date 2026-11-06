from django import forms
from django.db.models import Q

from .models import (
    AttendanceEntry,
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


class PortalModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "checkbox-input"
            else:
                field.widget.attrs["class"] = "form-control"
        for field in self.fields.values():
            if isinstance(field, forms.DateField):
                field.input_formats = ["%Y-%m-%d"]
            elif isinstance(field, forms.TimeField):
                field.input_formats = ["%H:%M", "%H:%M:%S"]


class OnboardingForm(PortalModelForm):
    class Meta:
        model = Onboarding
        fields = [
            "status",
            "assigned_hr_owner",
            "due_date",
            "details_collected",
            "documents_received",
            "nda_issued_signed",
            "joining_communication",
            "access_requested",
            "introduction_completed",
            "onboarding_marked_complete",
            "notes",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class OffboardingForm(PortalModelForm):
    class Meta:
        model = Offboarding
        fields = [
            "person",
            "department",
            "last_working_date",
            "reason_category",
            "hr_owner",
            "status",
            "due_date",
            "exit_communication",
            "handover_received",
            "pending_work_checked",
            "records_updated",
            "access_removal_requested",
            "nda_documents_checked",
            "exit_marked_complete",
            "notes",
        ]
        widgets = {
            "last_working_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        people = Person.objects.exclude(status=Person.Status.INACTIVE)
        if self.instance.pk:
            people = Person.objects.filter(Q(pk__in=people.values("pk")) | Q(pk=self.instance.person_id))
        self.fields["person"].queryset = people


class PersonForm(PortalModelForm):
    class Meta:
        model = Person
        fields = ["full_name", "role_department", "reporting_person", "contact_details", "start_date", "status", "notes"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class LeaveEntryForm(PortalModelForm):
    class Meta:
        model = LeaveEntry
        fields = ["person", "department", "leave_type", "from_date", "to_date", "reason", "status", "remarks"]
        widgets = {
            "from_date": forms.DateInput(attrs={"type": "date"}),
            "to_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.exclude(status=Person.Status.INACTIVE)


class AttendanceEntryForm(PortalModelForm):
    class Meta:
        model = AttendanceEntry
        fields = ["person", "department", "date", "status", "check_in", "check_out", "arrangement", "remarks"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "check_in": forms.TimeInput(attrs={"type": "time"}),
            "check_out": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.exclude(status=Person.Status.INACTIVE)


class EmployeeDocumentForm(PortalModelForm):
    class Meta:
        model = EmployeeDocument
        fields = ["person", "department", "category", "drive_link", "status", "date_received", "review_date", "remarks"]
        widgets = {
            "date_received": forms.DateInput(attrs={"type": "date"}),
            "review_date": forms.DateInput(attrs={"type": "date"}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.exclude(status=Person.Status.INACTIVE)
        self.fields["drive_link"].help_text = "Use an HTTPS link to the approved Google Drive file or folder."

    def clean_drive_link(self):
        link = self.cleaned_data.get("drive_link", "")
        if link and not link.startswith("https://"):
            raise forms.ValidationError("Drive links must use HTTPS.")
        return link


class NDARecordForm(PortalModelForm):
    class Meta:
        model = NDARecord
        fields = [
            "person_or_company",
            "department_relationship",
            "status",
            "sent_date",
            "signed_date",
            "drive_link",
            "responsible_hr_owner",
            "follow_up_date",
            "notes",
        ]
        widgets = {
            "sent_date": forms.DateInput(attrs={"type": "date"}),
            "signed_date": forms.DateInput(attrs={"type": "date"}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["drive_link"].help_text = "Use an HTTPS link to the approved Google Drive file or folder."

    def clean_drive_link(self):
        link = self.cleaned_data.get("drive_link", "")
        if link and not link.startswith("https://"):
            raise forms.ValidationError("Drive links must use HTTPS.")
        return link


class WebsiteAssetForm(PortalModelForm):
    class Meta:
        model = WebsiteAsset
        fields = [
            "section_name",
            "current_asset_link",
            "replacement_asset_link",
            "responsible_person",
            "requested_date",
            "status",
            "notes",
        ]
        widgets = {
            "requested_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_current_asset_link(self):
        return self._validate_https_link("current_asset_link")

    def clean_replacement_asset_link(self):
        return self._validate_https_link("replacement_asset_link")

    def _validate_https_link(self, field_name):
        link = self.cleaned_data.get(field_name, "")
        if link and not link.startswith("https://"):
            raise forms.ValidationError("Asset links must use HTTPS.")
        return link


class LinkedInCheckForm(PortalModelForm):
    class Meta:
        model = LinkedInCheck
        fields = [
            "person",
            "profile_url",
            "department",
            "assigned_reviewer",
            "last_checked_date",
            "profile_status",
            "check_status",
            "feedback_action_required",
            "next_check_date",
            "notes",
        ]
        widgets = {
            "last_checked_date": forms.DateInput(attrs={"type": "date"}),
            "next_check_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        people = Person.objects.exclude(status=Person.Status.INACTIVE)
        if self.instance.pk:
            people = Person.objects.filter(Q(pk__in=people.values("pk")) | Q(pk=self.instance.person_id))
        self.fields["person"].queryset = people


class FoundingTeamRequestForm(PortalModelForm):
    class Meta:
        model = FoundingTeamRequest
        fields = [
            "title",
            "description",
            "requester",
            "assigned_hr_owner",
            "priority",
            "due_date",
            "status",
            "follow_up_notes",
            "completion_notes",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "follow_up_notes": forms.Textarea(attrs={"rows": 3}),
            "completion_notes": forms.Textarea(attrs={"rows": 3}),
        }


class DepartmentalMeetingForm(PortalModelForm):
    class Meta:
        model = DepartmentalMeeting
        fields = [
            "department",
            "date",
            "time",
            "host",
            "attendees",
            "agenda_template",
            "agenda",
            "meeting_location",
            "meeting_link",
            "meeting_notes",
            "participation_notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
            "attendees": forms.Textarea(attrs={"rows": 2}),
            "agenda": forms.Textarea(attrs={"rows": 4}),
            "meeting_notes": forms.Textarea(attrs={"rows": 4}),
            "participation_notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agenda_template"].queryset = MeetingAgendaTemplate.objects.filter(is_active=True)
        self.fields["agenda_template"].required = False

    def save(self, commit=True):
        meeting = super().save(commit=False)
        if self.cleaned_data.get("agenda_template") and not meeting.agenda.strip():
            meeting.agenda = self.cleaned_data["agenda_template"].agenda
        if commit:
            meeting.save()
            self.save_m2m()
        return meeting

    def clean_meeting_link(self):
        link = self.cleaned_data.get("meeting_link", "")
        if link and not link.startswith("https://"):
            raise forms.ValidationError("Meeting links must use HTTPS.")
        return link


class MeetingAgendaTemplateForm(PortalModelForm):
    class Meta:
        model = MeetingAgendaTemplate
        fields = ["title", "agenda", "is_active"]
        widgets = {"agenda": forms.Textarea(attrs={"rows": 4})}


class MeetingActionItemForm(PortalModelForm):
    class Meta:
        model = MeetingActionItem
        fields = ["action_item", "owner", "due_date", "status", "completion_notes"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "completion_notes": forms.Textarea(attrs={"rows": 3}),
        }
