# Belvo Ventures Group — HR Operations Portal

A private HR-team console for Belvo Ventures Group. It covers the HR operations brief: HR-only sign-in, onboarding and offboarding, leave and attendance registers, employee document and NDA registers, website asset updates, manual LinkedIn checks, founding-team requests, and department meetings with agendas and action items. Employee accounts and employee self-service are intentionally not included.

## Requirements

- Python 3.10+
- pip

## Local setup

Run these commands from this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open the address printed by `runserver` (usually `http://127.0.0.1:8000/`) and sign in with the HR admin account. User accounts are created by an administrator; there is no public registration. Optional fictional walkthrough records can be added with:

```powershell
python manage.py seed_demo
```

The demo command is repeatable and creates no account or password.

## Included modules

- HR-only authentication using Django sessions and password hashing.
- Dashboard counts for active people, onboarding, pending leave, and attendance exceptions, plus near-term follow-ups.
- Onboarding records with the configurable starter checklist, HR owner, and due date.
- Leave register with validation, inclusive day counts, search, status filters, and CSV export.
- Onboarding and offboarding CSV exports that include status and checklist progress.
- Attendance register with search, status filters, CSV export, duplicate-day prevention, and audit events for creates/edits.
- Employee document register for approved Drive links, receipt status, categories, and review dates.
- NDA register with send/sign/follow-up statuses, due-date flags, and approved Drive links.
- Offboarding tracker with a seven-step checklist, owner and due-date tracking, overdue flags, and automatic person status updates when an exit starts or completes. Third-party account access must still be removed by the relevant administrator.
- Website photo/asset update tracker with collection, developer handoff, update, and verification statuses.
- Manual LinkedIn check register with reviewer, check outcome, next-check reminders, and LinkedIn-domain HTTPS link validation. No scraping or automated account access.
- Founding-team request log with priority, owners, follow-up notes, status, and due-date flags.
- Department meeting calendar with reusable agenda templates, notes, participation records, and owner/due-date action items.
- PostgreSQL support through `DATABASE_URL`, set up for Supabase. SQLite remains the default for local development.
- WhiteNoise static-file serving, Waitress WSGI server and a Render Blueprint for deployment.
- Django admin for authorized administrators to manage users and inspect HR records.

The deployment configuration is prepared, but the code must first be placed in a Belvo-controlled GitHub repository and connected to the company's Supabase project and Render account. This workspace has not been connected to either service.

## Privacy and production deployment

This app handles internal HR data. Do not expose a development server to the internet or use real personal data in demo environments. Before deployment:

1. Put this project in a **Belvo-controlled GitHub repository**. Do not deploy from the current `Iris-Classification` repository.
2. Create a Supabase PostgreSQL project. In its connection settings, select the **Session pooler** connection (port 5432) or a direct connection supported by your app host. Require SSL.
3. Before the first Render deploy, follow [Moving the local SQLite records to Supabase](#moving-the-local-sqlite-records-to-supabase) to preserve existing records.
4. In Render, create a **Blueprint** from the Belvo repository and its `render.yaml`. The Blueprint generates a Django secret; enter the Supabase session-pooler URL into the private `DATABASE_URL` environment variable when prompted. Never commit or share the connection URL or secret. The application enables SSL requirements in production and trusts Render's HTTPS proxy.
5. In `render.yaml`, update the service name/hostname values if the chosen Render service gets a different public hostname. Add any custom hostname to `DJANGO_ALLOWED_HOSTS` and its HTTPS origin to `DJANGO_CSRF_TRUSTED_ORIGINS`.
6. After the deploy is healthy, open Render Shell and run `python manage.py createsuperuser` to create the first HR login.
7. Restrict Supabase network/database access to the app and authorized maintainers. Enable backups and test restores before storing real HR data.

Production mode enables HTTPS redirects, secure session/CSRF cookies, and HSTS. Review proxy/HTTPS configuration and organizational retention requirements before going live. Google Drive files remain in the approved Drive; this portal stores only tracker metadata and links.

## Moving the local SQLite records to Supabase

The app stays on SQLite unless `DATABASE_URL` is set, so local work continues to use `db.sqlite3`. To preserve existing local records when creating the hosted database:

1. Stop the local development server. Make a protected copy of `db.sqlite3` before proceeding.
2. With `DATABASE_URL` **unset**, apply the current code migrations to the local SQLite database: `python manage.py migrate`.
3. Export the existing records to a local fixture that is ignored by Git:

   ```powershell
   python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission -e admin.LogEntry -e sessions --output local_data_backup.json
   ```

4. Set the Supabase `DATABASE_URL` as a secret environment variable in your app-host terminal/deployment service. Do not save it in this repository. For a local PowerShell import session:

   ```powershell
   $env:DATABASE_URL = "YOUR_SUPABASE_SESSION_POOLER_URL"
   $env:DJANGO_DEBUG = "0"
   $env:DJANGO_SECRET_KEY = "YOUR_DEPLOYMENT_SECRET"
   $env:DJANGO_ALLOWED_HOSTS = "YOUR_APP_HOSTNAME"
   $env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://YOUR_APP_HOSTNAME"
   ```

5. On the empty Supabase database, create tables up through the current portal schema with `python manage.py migrate hr_portal 0004`.
6. Import the fixture with `python manage.py loaddata local_data_backup.json`, then apply the final agenda-template data migration and any remaining migrations with `python manage.py migrate`.
7. Verify imported HR records and admin sign-in before switching users to the deployed app. Keep the protected SQLite copy and fixture until the migration is verified and a Supabase backup has been tested. Reset or rotate HR passwords if required by company policy.

Run the export while connected to SQLite and the import while connected to Supabase; confirm which database is selected before running data-changing commands. The backup/fixture may contain sensitive HR information, must stay private, and should be removed securely once the verified backups and migration are complete.

## Backups

For local development, stop the server and copy `db.sqlite3` to a protected backup location. For production, enable scheduled, encrypted Supabase backups and periodically test a restore into an isolated environment. Never store backups in the public static-files directory.

## Checks

```powershell
python manage.py check
python manage.py test
```
