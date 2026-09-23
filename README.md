# CIVICSENSE

CIVICSENSE is a full-stack civic issue reporting platform built with **Flask, MySQL, PyMySQL, HTML/CSS/JavaScript, Leaflet, and Chart.js**.

It lets citizens report community problems with GPS location and evidence photos, discover issues on an interactive map, support and comment on reports, and receive notifications as admins update issue status.

## Key Features

### Community features
- User registration, login and logout
- Password hashing with backward-compatible upgrade for legacy plaintext accounts
- Report civic issues with category, description and browser GPS coordinates
- **Evidence image upload** (validated, resized and stored in MySQL so images survive Render restarts)
- Interactive OpenStreetMap/Leaflet issue map
- Search and filter issues by text, category and status
- Issue detail page with location, evidence photo and full status history
- One support/upvote per user per issue
- Public comments: everyone can read; authenticated users can post
- Dark/light mode saved in the browser
- In-app notifications for report status changes and new comments on your own reports

### Admin features
- Separate administrator login
- Admin dashboard with live metrics
- Category, status and monthly report charts
- Change issue status: **Open → In Progress → Resolved**
- Add a status-change note
- Automatic status history timeline
- Delete issues and related comments/votes/images/history
- Delete comments
- Admin account automatically created/promoted from environment variables

### Deployment features
- `.env` support for local development
- Render `render.yaml` included
- Gunicorn start command configured
- Health endpoint: `/health`
- Automatic schema creation/migration on application startup
- Fresh database `setup.sql`
- Manual migration helper `migrate_existing.sql`
- Credentials excluded from Git with `.gitignore`

## Project Structure

```text
civicsense/
├── app.py
├── requirements.txt
├── setup.sql
├── migrate_existing.sql
├── .env.example
├── .gitignore
├── .python-version
├── render.yaml
├── README.md
├── static/
│   ├── app.js
│   └── style.css
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── report_issue.html
    ├── view_issues.html
    ├── issue_detail.html
    ├── map.html
    ├── admin_dashboard.html
    └── notifications.html
```

## Local Setup

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Create `.env`

Copy `.env.example` to `.env` and fill in your MySQL/Aiven details:

```env
MYSQL_HOST=your-aiven-host
MYSQL_PORT=14016
MYSQL_USER=avnadmin
MYSQL_PASSWORD=your-aiven-password
MYSQL_DB=civicsense_prod
SECRET_KEY=replace-with-a-long-random-secret
COOKIE_SECURE=0

ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-this-to-a-strong-password
```

Keep `.env` private. Never commit it.

### 4. Start the app

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

The Flask app automatically creates the required tables and adds missing columns for the new features. For a fresh database you can also run `setup.sql` manually.

## MySQL Setup

### Fresh database

Run:

```bash
mysql -u root -p < setup.sql
```

### Existing CIVICSENSE database

The application automatically creates the new feature tables and adds the `issues.reported_by`/auth columns on startup. `migrate_existing.sql` is included for teams that prefer a manual migration first.

**Do not run a destructive reset against a database containing production data.**

## Aiven MySQL

The application works with Aiven MySQL. Use the connection information from your Aiven service in `.env` or Render environment variables.

For local Windows testing, if your DNS resolver cannot resolve the Aiven hostname but the service IP is reachable, the Aiven IP can be used temporarily. For Render, use Aiven's hostname from the Aiven connection information.

## Render Deployment

This repository includes `render.yaml`.

Recommended Render service configuration:

```text
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app --bind 0.0.0.0:$PORT

Health Check:
/health
```

Environment variables:

```text
MYSQL_HOST
MYSQL_PORT
MYSQL_USER
MYSQL_PASSWORD
MYSQL_DB
SECRET_KEY
COOKIE_SECURE=1
ADMIN_EMAIL
ADMIN_PASSWORD
```

Do not upload `.env` to GitHub.

## Database Design

Main tables:

- `users` — accounts and roles
- `issues` — civic reports, location, status and support count
- `issue_votes` — one support vote per user per issue
- `comments` — public community discussion
- `issue_images` — one validated evidence image per issue
- `issue_status_history` — transparent status timeline
- `notifications` — in-app user notifications

## Image Storage

Uploaded evidence images are validated with Pillow, resized, converted to JPEG, and stored as a MySQL `LONGBLOB`. This avoids relying on Render's ephemeral local filesystem for persistent uploads.

## Public Comments

Comments are intentionally **visible to all visitors**. Only authenticated users can create comments, and only administrators can delete comments.

## Security Notes

- Passwords are hashed with Werkzeug password hashing.
- CSRF tokens protect POST forms.
- Database credentials are read from environment variables.
- `.env` is excluded from version control.
- Uploaded images are validated and size-limited.
- Admin actions require the admin role.

## Routes

```text
/                       Issue feed
/issues                 Search/filter issue feed
/issue/<id>             Issue details + history + comments
/map                    Interactive issue map
/api/issues             Map data JSON endpoint
/report                 Authenticated reporting form
/login                  Public user login
/register               Public user registration
/admin/login            Admin login
/admin/dashboard        Admin analytics
/notifications         User notifications
/health                 Render health endpoint
```

## GitHub

Example repository:

```text
https://github.com/souravkeshri-14/CIVICSENSE
```

## Author

**Sourav Keshri**


## Issue Review Workflow

New reports are created with status **Not Opened**. An administrator reviews the report and can then move it to **Open**, **In Progress**, or **Resolved**.

## Location Accuracy

Reporters can use high-accuracy browser geolocation and can click the map or drag the marker to correct the exact issue location. GPS accuracy is stored with the report and shown on maps when available.
