from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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


class PortalAccessTests(TestCase):
    def test_dashboard_redirects_to_login_for_anonymous_users(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_tracker_pages_require_hr_login(self):
        routes = [
            "onboarding-list",
            "offboarding-list",
            "leave-list",
            "attendance-list",
            "document-list",
            "nda-list",
            "website-asset-list",
            "linkedin-list",
            "founding-request-list",
            "meeting-list",
            "agenda-template-list",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertRedirects(response, f"{reverse('login')}?next={reverse(route)}")

    def test_login_page_has_no_public_registration(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Create account")
        self.assertContains(response, "HR team")

    def test_hr_user_can_sign_in_and_reach_dashboard(self):
        user = get_user_model().objects.create_user(username="hr-login", password="Strong-demo-password-123")
        self.assertTrue(self.client.login(username="hr-login", password="Strong-demo-password-123"))
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HR operations overview")

    def test_authenticated_hr_can_open_mvp_pages(self):
        user = get_user_model().objects.create_user(username="hr-viewer", password="Strong-demo-password-123")
        self.client.force_login(user)
        for route in [
            "dashboard",
            "onboarding-list",
            "onboarding-create",
            "onboarding-export",
            "offboarding-list",
            "offboarding-create",
            "offboarding-export",
            "website-asset-list",
            "website-asset-create",
            "linkedin-list",
            "linkedin-create",
            "founding-request-list",
            "founding-request-create",
            "meeting-list",
            "meeting-create",
            "agenda-template-list",
            "agenda-template-create",
            "leave-list",
            "leave-create",
            "attendance-list",
            "attendance-create",
            "document-list",
            "document-create",
            "nda-list",
            "nda-create",
        ]:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 200)
        self.assertTrue(MeetingAgendaTemplate.objects.filter(title="Daily Department Sync", is_active=True).exists())


class OnboardingTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="hr-admin", password="Strong-demo-password-123")
        self.client.force_login(user)

    def test_create_and_update_onboarding(self):
        response = self.client.post(
            reverse("onboarding-create"),
            {
                "person-full_name": "Demo Person",
                "person-role_department": "Product",
                "person-reporting_person": "Team Lead",
                "person-contact_details": "",
                "person-start_date": "2026-12-01",
                "person-status": Person.Status.ONBOARDING,
                "person-notes": "",
                "onboarding-status": Onboarding.Status.IN_PROGRESS,
                "onboarding-assigned_hr_owner": "HR",
                "onboarding-due_date": "2026-12-05",
                "onboarding-details_collected": "on",
                "onboarding-documents_received": "",
                "onboarding-nda_issued_signed": "",
                "onboarding-joining_communication": "",
                "onboarding-access_requested": "",
                "onboarding-introduction_completed": "",
                "onboarding-onboarding_marked_complete": "",
                "onboarding-notes": "",
            },
        )
        self.assertRedirects(response, reverse("onboarding-list"))
        onboarding = Onboarding.objects.get()
        self.assertEqual(onboarding.person.full_name, "Demo Person")
        self.assertTrue(onboarding.details_collected)
        self.assertTrue(AuditEvent.objects.filter(action="created").exists())

        response = self.client.post(
            reverse("onboarding-edit", args=[onboarding.pk]),
            {
                "person-full_name": "Demo Person",
                "person-role_department": "Product",
                "person-reporting_person": "Team Lead",
                "person-contact_details": "",
                "person-start_date": "2026-12-01",
                "person-status": Person.Status.ACTIVE,
                "person-notes": "",
                "onboarding-status": Onboarding.Status.COMPLETED,
                "onboarding-assigned_hr_owner": "HR",
                "onboarding-due_date": "2026-12-05",
                "onboarding-details_collected": "on",
                "onboarding-documents_received": "on",
                "onboarding-nda_issued_signed": "on",
                "onboarding-joining_communication": "on",
                "onboarding-access_requested": "on",
                "onboarding-introduction_completed": "on",
                "onboarding-onboarding_marked_complete": "on",
            },
        )
        self.assertRedirects(response, reverse("onboarding-list"))
        onboarding.refresh_from_db()
        self.assertEqual(onboarding.status, Onboarding.Status.COMPLETED)
        self.assertEqual(AuditEvent.objects.filter(action="updated").count(), 1)


class OffboardingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-exits", password="Strong-demo-password-123")
        self.client.force_login(self.user)
        self.person = Person.objects.create(
            full_name="Exiting Teammate",
            role_department="Engineering",
            status=Person.Status.ACTIVE,
        )

    def _offboarding_data(self, **overrides):
        data = {
            "person": self.person.pk,
            "department": "Engineering",
            "last_working_date": "2026-12-01",
            "reason_category": "Internship completed",
            "hr_owner": "HR",
            "status": Offboarding.Status.IN_PROGRESS,
            "due_date": "2026-12-03",
            "exit_communication": "on",
            "handover_received": "",
            "pending_work_checked": "",
            "records_updated": "",
            "access_removal_requested": "",
            "nda_documents_checked": "",
            "exit_marked_complete": "",
            "notes": "",
        }
        data.update(overrides)
        return data

    def test_create_offboarding_updates_person_status_and_audits(self):
        response = self.client.post(reverse("offboarding-create"), self._offboarding_data())
        self.assertRedirects(response, reverse("offboarding-list"))
        record = Offboarding.objects.get()
        self.person.refresh_from_db()
        self.assertEqual(self.person.status, Person.Status.OFFBOARDING)
        self.assertEqual(record.person, self.person)
        self.assertTrue(AuditEvent.objects.filter(record_type="hr_portal.Offboarding", action="created").exists())

    def test_incomplete_checklist_cannot_be_marked_completed(self):
        response = self.client.post(
            reverse("offboarding-create"),
            self._offboarding_data(status=Offboarding.Status.COMPLETED, exit_marked_complete="on"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Offboarding.objects.count(), 0)
        self.assertEqual(self.person.status, Person.Status.ACTIVE)
        self.assertContains(response, "Complete every exit checklist item")

    def test_completed_offboarding_requires_checklist_and_marks_person_inactive(self):
        checklist = {
            "exit_communication": "on",
            "handover_received": "on",
            "pending_work_checked": "on",
            "records_updated": "on",
            "access_removal_requested": "on",
            "nda_documents_checked": "on",
            "exit_marked_complete": "on",
        }
        response = self.client.post(
            reverse("offboarding-create"),
            self._offboarding_data(status=Offboarding.Status.COMPLETED, **checklist),
        )
        self.assertRedirects(response, reverse("offboarding-list"))
        self.person.refresh_from_db()
        self.assertEqual(self.person.status, Person.Status.INACTIVE)
        self.assertEqual(Offboarding.objects.get().checklist_completed_count, 7)

    def test_overdue_flags_and_dashboard_count_active_exits(self):
        overdue_date = date.today().replace(day=1) - date.resolution
        Offboarding.objects.create(
            person=self.person,
            department="Engineering",
            last_working_date=overdue_date,
            status=Offboarding.Status.WAITING,
            due_date=overdue_date,
        )
        list_response = self.client.get(reverse("offboarding-list"))
        self.assertContains(list_response, "Overdue")
        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertEqual(dashboard_response.context["offboarding_count"], 1)
        self.assertEqual(dashboard_response.context["overdue_offboarding_count"], 1)

    def test_onboarding_and_offboarding_exports_are_hr_only(self):
        response = self.client.get(reverse("offboarding-export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Last working date", response.content.decode())

        self.client.logout()
        response = self.client.get(reverse("onboarding-export"))
        self.assertEqual(response.status_code, 302)


class TrackerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-member", password="Strong-demo-password-123")
        self.client.force_login(self.user)
        self.person = Person.objects.create(full_name="Sample Teammate", role_department="Engineering", status=Person.Status.ACTIVE)

    def test_leave_days_are_calculated_and_invalid_dates_are_rejected(self):
        response = self.client.post(
            reverse("leave-create"),
            {
                "person": self.person.pk,
                "department": "Engineering",
                "leave_type": "Personal",
                "from_date": "2026-11-10",
                "to_date": "2026-11-12",
                "reason": "Personal",
                "status": LeaveEntry.Status.PENDING,
                "remarks": "",
            },
        )
        self.assertRedirects(response, reverse("leave-list"))
        self.assertEqual(LeaveEntry.objects.get().number_of_days, 3)

        response = self.client.post(
            reverse("leave-create"),
            {
                "person": self.person.pk,
                "department": "Engineering",
                "leave_type": "Personal",
                "from_date": "2026-11-12",
                "to_date": "2026-11-10",
                "status": LeaveEntry.Status.PENDING,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LeaveEntry.objects.count(), 1)
        self.assertContains(response, "end date must be on or after")

    def test_attendance_edit_is_audited_and_duplicate_day_is_rejected(self):
        entry = AttendanceEntry.objects.create(
            person=self.person,
            department="Engineering",
            date=date.today(),
            status=AttendanceEntry.Status.PRESENT,
            updated_by=self.user,
        )
        response = self.client.post(
            reverse("attendance-edit", args=[entry.pk]),
            {
                "person": self.person.pk,
                "department": "Engineering",
                "date": date.today().isoformat(),
                "status": AttendanceEntry.Status.LATE,
                "check_in": "09:45",
                "check_out": "",
                "arrangement": AttendanceEntry.Arrangement.OFFICE,
                "remarks": "Demo update",
            },
        )
        self.assertRedirects(response, reverse("attendance-list"))
        entry.refresh_from_db()
        self.assertEqual(entry.status, AttendanceEntry.Status.LATE)
        audit = AuditEvent.objects.get(action="updated", record_type="hr_portal.AttendanceEntry")
        self.assertEqual(audit.changes["Status"], {"before": "present", "after": "late"})

        response = self.client.post(
            reverse("attendance-create"),
            {
                "person": self.person.pk,
                "department": "Engineering",
                "date": date.today().isoformat(),
                "status": AttendanceEntry.Status.PRESENT,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AttendanceEntry.objects.count(), 1)
        self.assertContains(response, "Attendance entry with this Person and Date already exists")

    def test_csv_exports_require_login_and_return_register_headers(self):
        self.client.logout()
        response = self.client.get(reverse("leave-export"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse("attendance-export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("Person,Department,Date,Status", response.content.decode())

    def test_attendance_month_filter_limits_the_register(self):
        AttendanceEntry.objects.create(
            person=self.person,
            department="Engineering",
            date=date(2026, 3, 15),
            status=AttendanceEntry.Status.PRESENT,
            updated_by=self.user,
        )
        AttendanceEntry.objects.create(
            person=self.person,
            department="Engineering",
            date=date(2026, 4, 15),
            status=AttendanceEntry.Status.PRESENT,
            updated_by=self.user,
        )
        response = self.client.get(reverse("attendance-list"), {"month": "2026-03"})
        self.assertContains(response, "15 Mar 2026")
        self.assertNotContains(response, "15 Apr 2026")


class DocumentAndNdaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-docs", password="Strong-demo-password-123")
        self.client.force_login(self.user)
        self.person = Person.objects.create(
            full_name="Document Teammate",
            role_department="People",
            status=Person.Status.ACTIVE,
        )

    def test_document_create_and_edit_keeps_drive_link_out_of_audit_values(self):
        response = self.client.post(
            reverse("document-create"),
            {
                "person": self.person.pk,
                "department": "People",
                "category": EmployeeDocument.Category.JOINING,
                "drive_link": "https://drive.google.com/drive/folders/example",
                "status": EmployeeDocument.Status.RECEIVED,
                "date_received": "2026-11-06",
                "review_date": "",
                "remarks": "Joining documents received",
            },
        )
        self.assertRedirects(response, reverse("document-list"))
        record = EmployeeDocument.objects.get()
        self.assertEqual(record.person, self.person)
        self.assertEqual(record.status, EmployeeDocument.Status.RECEIVED)
        self.assertContains(self.client.get(reverse("document-list")), "Open Drive")

        response = self.client.post(
            reverse("document-edit", args=[record.pk]),
            {
                "person": self.person.pk,
                "department": "People",
                "category": EmployeeDocument.Category.JOINING,
                "drive_link": "https://drive.google.com/drive/folders/updated-example",
                "status": EmployeeDocument.Status.REQUESTED,
                "date_received": "",
                "review_date": "",
                "remarks": "Following up",
            },
        )
        self.assertRedirects(response, reverse("document-list"))
        audit = AuditEvent.objects.get(record_type="hr_portal.EmployeeDocument", action="updated")
        self.assertEqual(audit.changes["Drive link"], "Updated")
        self.assertNotIn("updated-example", str(audit.changes))

    def test_document_links_require_https(self):
        response = self.client.post(
            reverse("document-create"),
            {
                "person": self.person.pk,
                "department": "People",
                "category": EmployeeDocument.Category.IDENTITY,
                "drive_link": "http://drive.google.com/folder",
                "status": EmployeeDocument.Status.REQUESTED,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EmployeeDocument.objects.count(), 0)
        self.assertContains(response, "Drive links must use HTTPS")

    def test_nda_follow_up_overdue_and_signed_status(self):
        overdue = NDARecord.objects.create(
            person_or_company="Example Partner",
            department_relationship="Vendor",
            status=NDARecord.Status.PENDING_FOLLOW_UP,
            follow_up_date=date.today().replace(day=1) - date.resolution,
            responsible_hr_owner="HR",
        )
        signed = NDARecord.objects.create(
            person_or_company="Signed Partner",
            status=NDARecord.Status.SIGNED,
            follow_up_date=date.today().replace(day=1) - date.resolution,
        )
        response = self.client.get(reverse("nda-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overdue")
        self.assertContains(response, overdue.person_or_company)
        self.assertContains(response, signed.person_or_company)

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.context["pending_nda_count"], 1)

    def test_nda_can_be_created_with_private_drive_link(self):
        response = self.client.post(
            reverse("nda-create"),
            {
                "person_or_company": "Example Intern",
                "department_relationship": "Engineering",
                "status": NDARecord.Status.SENT,
                "sent_date": "2026-11-06",
                "signed_date": "",
                "drive_link": "https://drive.google.com/file/d/example",
                "responsible_hr_owner": "HR",
                "follow_up_date": "2026-11-10",
                "notes": "",
            },
        )
        self.assertRedirects(response, reverse("nda-list"))
        record = NDARecord.objects.get()
        self.assertEqual(record.status, NDARecord.Status.SENT)
        self.assertTrue(AuditEvent.objects.filter(record_type="hr_portal.NDARecord", action="created").exists())


class RemainingPortalModulesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-coordination", password="Strong-demo-password-123")
        self.client.force_login(self.user)
        self.person = Person.objects.create(
            full_name="Review Intern",
            role_department="Product",
            status=Person.Status.ACTIVE,
        )

    def test_website_asset_create_and_http_link_validation(self):
        response = self.client.post(
            reverse("website-asset-create"),
            {
                "section_name": "Team page",
                "current_asset_link": "https://drive.google.com/current",
                "replacement_asset_link": "https://drive.google.com/new",
                "responsible_person": "HR",
                "requested_date": "2026-11-06",
                "status": WebsiteAsset.Status.READY_TO_SHARE,
                "notes": "",
            },
        )
        self.assertRedirects(response, reverse("website-asset-list"))
        asset = WebsiteAsset.objects.get()
        self.assertEqual(asset.status, WebsiteAsset.Status.READY_TO_SHARE)
        self.assertTrue(AuditEvent.objects.filter(record_type="hr_portal.WebsiteAsset", action="created").exists())

        response = self.client.post(
            reverse("website-asset-create"),
            {
                "section_name": "Bad link page",
                "current_asset_link": "http://example.test/asset",
                "status": WebsiteAsset.Status.PENDING_COLLECTION,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(WebsiteAsset.objects.count(), 1)

    def test_linkedin_manual_review_cannot_accept_non_linkedin_url_or_missing_done_date(self):
        base_data = {
            "person": self.person.pk,
            "profile_url": "https://www.linkedin.com/in/review-intern",
            "department": "Product",
            "assigned_reviewer": "HR",
            "last_checked_date": "",
            "profile_status": LinkedInCheck.ProfileStatus.CURRENT,
            "check_status": LinkedInCheck.Status.DONE,
            "feedback_action_required": "",
            "next_check_date": "",
            "notes": "",
        }
        response = self.client.post(reverse("linkedin-create"), base_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LinkedInCheck.objects.count(), 0)
        self.assertContains(response, "Enter the date this profile was checked")

        base_data["profile_url"] = "https://linkedin.com.example.test/in/fake"
        base_data["last_checked_date"] = "2026-11-06"
        response = self.client.post(reverse("linkedin-create"), base_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LinkedInCheck.objects.count(), 0)
        self.assertContains(response, "valid HTTPS LinkedIn profile link")

    def test_request_overdue_indicator_and_audit(self):
        response = self.client.post(
            reverse("founding-request-create"),
            {
                "title": "Prepare founder briefing",
                "description": "Collect the meeting documents",
                "requester": "Founding team",
                "assigned_hr_owner": "HR",
                "priority": FoundingTeamRequest.Priority.HIGH,
                "due_date": "2026-11-01",
                "status": FoundingTeamRequest.Status.NEW,
                "follow_up_notes": "",
                "completion_notes": "",
            },
        )
        self.assertRedirects(response, reverse("founding-request-list"))
        self.assertTrue(AuditEvent.objects.filter(record_type="hr_portal.FoundingTeamRequest").exists())
        self.assertContains(self.client.get(reverse("founding-request-list")), "Overdue")

    def test_meeting_agenda_template_and_action_items(self):
        template = MeetingAgendaTemplate.objects.create(
            title="Daily team sync",
            agenda="1. Updates\n2. Blockers\n3. Actions",
        )
        response = self.client.post(
            reverse("meeting-create"),
            {
                "department": "Product",
                "date": "2026-11-06",
                "time": "10:00",
                "host": "Team lead",
                "attendees": "Design, Product",
                "agenda_template": template.pk,
                "agenda": "",
                "meeting_location": "Meeting room",
                "meeting_link": "",
                "meeting_notes": "",
                "participation_notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        meeting = DepartmentalMeeting.objects.get()
        self.assertEqual(meeting.agenda, template.agenda)
        self.assertTrue(AuditEvent.objects.filter(record_type="hr_portal.DepartmentalMeeting").exists())

        response = self.client.post(
            reverse("meeting-detail", args=[meeting.pk]),
            {
                "action_item": "Share design draft",
                "owner": "Designer",
                "due_date": "2026-11-07",
                "status": MeetingActionItem.Status.PENDING,
                "completion_notes": "",
            },
        )
        self.assertRedirects(response, reverse("meeting-detail", args=[meeting.pk]))
        self.assertEqual(meeting.action_items.get().owner, "Designer")
        self.assertTrue(AuditEvent.objects.filter(record_type="hr_portal.MeetingActionItem").exists())

        action_item = meeting.action_items.get()
        response = self.client.post(
            reverse("meeting-action-edit", args=[meeting.pk, action_item.pk]),
            {
                "action_item": "Share design draft",
                "owner": "Designer",
                "due_date": "2026-11-07",
                "status": MeetingActionItem.Status.COMPLETED,
                "completion_notes": "Draft shared",
            },
        )
        self.assertRedirects(response, reverse("meeting-detail", args=[meeting.pk]))
        action_item.refresh_from_db()
        self.assertEqual(action_item.status, MeetingActionItem.Status.COMPLETED)

        response = self.client.post(
            reverse("meeting-edit", args=[meeting.pk]),
            {
                "department": "Product",
                "date": "2026-11-06",
                "time": "10:00",
                "host": "Team lead",
                "attendees": "Design, Product",
                "agenda_template": template.pk,
                "agenda": "1. Updates\n2. Blockers\n3. Actions",
                "meeting_location": "Meeting room",
                "meeting_link": "",
                "meeting_notes": "Private notes: review the draft",
                "participation_notes": "",
            },
        )
        self.assertRedirects(response, reverse("meeting-detail", args=[meeting.pk]))
        meeting_audit = AuditEvent.objects.get(
            record_type="hr_portal.DepartmentalMeeting",
            action="updated",
        )
        self.assertEqual(meeting_audit.changes["Meeting notes"], "Updated")
        self.assertNotIn("Private notes", str(meeting_audit.changes))
