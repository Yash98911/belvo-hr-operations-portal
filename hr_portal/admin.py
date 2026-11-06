from django.contrib import admin

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


class AuditedModelAdmin(admin.ModelAdmin):
    protected_fields = {
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

    def save_model(self, request, obj, form, change):
        changes = {}
        if change:
            for field_name in form.changed_data:
                label = str(form.fields[field_name].label)
                if field_name in self.protected_fields:
                    changes[label] = "Updated"
                else:
                    before = form.initial.get(field_name)
                    after = form.cleaned_data.get(field_name)
                    changes[label] = {
                        "before": str(before) if before is not None else "",
                        "after": str(after) if after is not None else "",
                    }

        if isinstance(obj, LeaveEntry):
            obj.recorded_by = request.user
        elif isinstance(obj, AttendanceEntry):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        if isinstance(obj, Offboarding):
            person_status = Person.Status.INACTIVE if obj.status == Offboarding.Status.COMPLETED else Person.Status.OFFBOARDING
            person = obj.person
            if person.status != person_status:
                person.status = person_status
                person.save(update_fields=["status", "updated_at"])
        action = "updated" if change else "created"
        AuditEvent.objects.create(
            actor=request.user,
            action=action,
            record_type=obj._meta.label,
            record_id=obj.pk,
            summary=f"{obj._meta.verbose_name.title()} {action}",
            changes=changes,
        )


@admin.register(Person)
class PersonAdmin(AuditedModelAdmin):
    list_display = ["full_name", "role_department", "status", "start_date"]
    list_filter = ["status", "role_department"]
    search_fields = ["full_name", "role_department"]


@admin.register(Onboarding)
class OnboardingAdmin(AuditedModelAdmin):
    list_display = ["person", "status", "assigned_hr_owner", "due_date"]
    list_filter = ["status"]
    search_fields = ["person__full_name", "assigned_hr_owner"]


@admin.register(Offboarding)
class OffboardingAdmin(AuditedModelAdmin):
    list_display = ["person", "department", "last_working_date", "status", "hr_owner", "due_date"]
    list_filter = ["status", "department"]
    search_fields = ["person__full_name", "department", "hr_owner"]


@admin.register(LeaveEntry)
class LeaveEntryAdmin(AuditedModelAdmin):
    list_display = ["person", "department", "leave_type", "from_date", "to_date", "status"]
    list_filter = ["status", "department", "leave_type"]
    search_fields = ["person__full_name", "department"]


@admin.register(AttendanceEntry)
class AttendanceEntryAdmin(AuditedModelAdmin):
    list_display = ["person", "department", "date", "status", "updated_by", "updated_at"]
    list_filter = ["status", "date", "department"]
    search_fields = ["person__full_name", "department"]


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(AuditedModelAdmin):
    list_display = ["person", "department", "category", "status", "date_received", "review_date"]
    list_filter = ["status", "category", "department"]
    search_fields = ["person__full_name", "department", "remarks"]


@admin.register(NDARecord)
class NDARecordAdmin(AuditedModelAdmin):
    list_display = ["person_or_company", "department_relationship", "status", "responsible_hr_owner", "follow_up_date"]
    list_filter = ["status", "department_relationship"]
    search_fields = ["person_or_company", "responsible_hr_owner"]


@admin.register(WebsiteAsset)
class WebsiteAssetAdmin(AuditedModelAdmin):
    list_display = ["section_name", "responsible_person", "requested_date", "status", "last_updated"]
    list_filter = ["status", "requested_date"]
    search_fields = ["section_name", "responsible_person"]


@admin.register(LinkedInCheck)
class LinkedInCheckAdmin(AuditedModelAdmin):
    list_display = ["person", "department", "check_status", "last_checked_date", "next_check_date", "assigned_reviewer"]
    list_filter = ["check_status", "profile_status", "department"]
    search_fields = ["person__full_name", "department", "assigned_reviewer"]


@admin.register(FoundingTeamRequest)
class FoundingTeamRequestAdmin(AuditedModelAdmin):
    list_display = ["title", "requester", "assigned_hr_owner", "priority", "due_date", "status"]
    list_filter = ["status", "priority", "due_date"]
    search_fields = ["title", "requester", "assigned_hr_owner"]


class MeetingActionItemInline(admin.TabularInline):
    model = MeetingActionItem
    extra = 0


@admin.register(DepartmentalMeeting)
class DepartmentalMeetingAdmin(AuditedModelAdmin):
    list_display = ["department", "date", "time", "host"]
    list_filter = ["department", "date"]
    search_fields = ["department", "host", "attendees"]
    inlines = [MeetingActionItemInline]


@admin.register(MeetingAgendaTemplate)
class MeetingAgendaTemplateAdmin(AuditedModelAdmin):
    list_display = ["title", "is_active", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["title"]


@admin.register(MeetingActionItem)
class MeetingActionItemAdmin(AuditedModelAdmin):
    list_display = ["action_item", "meeting", "owner", "due_date", "status"]
    list_filter = ["status", "due_date"]
    search_fields = ["action_item", "owner", "meeting__department"]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "action", "record_type", "record_id", "summary"]
    list_filter = ["action", "record_type", "created_at"]
    search_fields = ["summary", "actor__username"]
    readonly_fields = ["created_at", "actor", "action", "record_type", "record_id", "summary", "changes"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
