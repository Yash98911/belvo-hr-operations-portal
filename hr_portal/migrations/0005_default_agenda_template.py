from django.db import migrations


def add_default_agenda_template(apps, schema_editor):
    template = apps.get_model("hr_portal", "MeetingAgendaTemplate")
    template.objects.using(schema_editor.connection.alias).get_or_create(
        title="Daily Department Sync",
        defaults={
            "agenda": "1. Team updates\n2. Priorities for today\n3. Blockers and support needed\n4. Action items and owners",
            "is_active": True,
        },
    )


def remove_default_agenda_template(apps, schema_editor):
    template = apps.get_model("hr_portal", "MeetingAgendaTemplate")
    template.objects.using(schema_editor.connection.alias).filter(title="Daily Department Sync").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("hr_portal", "0004_meetingagendatemplate_foundingteamrequest_and_more"),
    ]

    operations = [
        migrations.RunPython(add_default_agenda_template, remove_default_agenda_template),
    ]
