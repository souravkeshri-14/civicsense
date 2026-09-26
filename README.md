# 🏙️ CIVICSENSE

CIVICSENSE is a full-stack civic issue reporting platform built with **Flask, MySQL, PyMySQL, HTML/CSS/JavaScript, Leaflet, and Chart.js**.

It lets citizens report community problems with GPS location and evidence photos, discover issues on an interactive map, support and comment on reports, and receive notifications as admins update issue status.

<p align="left">
  <a href="https://github.com/souravkeshri-14/civicsense">
    <img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github" alt="GitHub Repository">
  </a>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white" alt="MySQL">
  <img src="https://img.shields.io/badge/PyMySQL-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="PyMySQL">
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="JavaScript">
  <img src="https://img.shields.io/badge/Leaflet-199900?style=for-the-badge&logo=leaflet&logoColor=white" alt="Leaflet">
  <img src="https://img.shields.io/badge/Chart.js-FF6384?style=for-the-badge&logo=chart.js&logoColor=white" alt="Chart.js">
  <img src="https://img.shields.io/badge/Aiven-MySQL-FF5A1F?style=for-the-badge&logo=aiven&logoColor=white" alt="Aiven MySQL">
  <img src="https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=black" alt="Render">
</p>

## 🚀 Live Demo

**Live App:** https://civicsense-hm6y.onrender.com/issues

**Deployed using:** Render

**Database:** Aiven MySQL

---

## 📌 Key Features

### 👥 Community Features

- User registration, login, and logout
- Password hashing with backward-compatible upgrade for legacy plaintext accounts
- Report civic issues with category, description, and browser GPS coordinates
- **Evidence image upload** with validation and resizing
- Evidence images stored in **MySQL** so they persist across Render restarts
- Interactive **OpenStreetMap + Leaflet** issue map
- Search and filter issues by text, category, and status
- Issue detail page with location, evidence photo, and complete status history
- One support/upvote per user per issue
- Public comments visible to everyone
- Authenticated users can post comments
- Dark/light mode saved in the browser
- In-app notifications for report status changes and new comments on your own reports

### 🛡️ Admin Features

- Separate administrator login
- Admin dashboard with live metrics
- Category, status, and monthly report charts using Chart.js
- Change issue status: **Not Opened → Open → In Progress → Resolved**
- Add a status-change note
- Automatic status history timeline
- Delete issues and related comments, votes, images, and history
- Delete comments
- Admin account automatically created/promoted from environment variables

### ☁️ Deployment Features

- `.env` support for local development
- Render `render.yaml` included
- Gunicorn start command configured
- Health endpoint: `/health`
- Automatic schema creation/migration on application startup
- Fresh database schema in `setup.sql`
- Manual migration helper in `migrate_existing.sql`
- Credentials excluded from Git with `.gitignore`

---

## 🛠️ Technologies Used

- **Python**
- **Flask**
- **MySQL**
- **PyMySQL**
- **HTML5**
- **CSS3**
- **JavaScript**
- **Leaflet.js**
- **OpenStreetMap**
- **Chart.js**
- **Pillow**
- **Gunicorn**
- **Render**
- **Aiven MySQL**

---

## 📂 Project Structure

```text
civicsense/
│
├── app.py
├── requirements.txt
├── setup.sql
├── migrate_existing.sql
├── .env.example
├── .gitignore
├── .python-version
├── render.yaml
├── README.md
│
├── static/
│   ├── app.js
│   └── style.css
│
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

---

## ⚙️ Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/souravkeshri-14/civicsense.git
cd civicsense
```

### 2. Create and Activate a Virtual Environment

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Windows CMD

```cmd
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env`

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

Keep `.env` private. **Never commit it.**

### 5. Start the App

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

The application automatically creates required tables and missing columns on startup. For a fresh database, you can also run `setup.sql` manually.

---

## 🗄️ MySQL Setup

### Fresh Database

```bash
mysql -u root -p < setup.sql
```

### Existing CIVICSENSE Database

The application automatically creates new feature tables and adds required columns during startup. `migrate_existing.sql` is included for teams that prefer a manual migration first.

**Do not run a destructive reset against production data.**

---

## ☁️ Aiven MySQL

CIVICSENSE works directly with **Aiven MySQL**. Use the host, port, username, password, and database name from your Aiven service in `.env` or Render environment variables.

For production, use the Aiven hostname from **Connection information** rather than hardcoding a service IP address.

---

## 🚀 Render Deployment

This repository includes `render.yaml`.

Recommended Render configuration:

```text
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app --bind 0.0.0.0:$PORT

Health Check:
/health
```

### Environment Variables

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

Do **not** upload `.env` to GitHub.

---

## 🗺️ Interactive Issue Map

The issue map uses **Leaflet** and **OpenStreetMap**.

Features include:

- Issue markers
- Status-based marker styling
- Issue details in map popups
- Location accuracy information when available
- Interactive map navigation
- Browser-based location detection
- User-adjustable issue location using map interaction

---

## 📸 Evidence Image Storage

Uploaded evidence images are:

- Validated with Pillow
- Size-limited
- Resized
- Converted to JPEG
- Stored in MySQL as `LONGBLOB`

This avoids relying on Render's ephemeral local filesystem for persistent uploads.

---

## 💬 Public Comments

Comments are intentionally **visible to all visitors**.

- Everyone can read comments
- Authenticated users can post comments
- Administrators can delete comments

---

## 🔄 Issue Review Workflow

New reports start with:

```text
Not Opened
    ↓
Open
    ↓
In Progress
    ↓
Resolved
```

Administrators review reports and update their status. Every status change can include an admin note and is stored in status history.

---

## 🔔 Notifications

Users can receive in-app notifications when:

- Their issue status changes
- Someone comments on their report

Notifications include unread/read state and can be marked as read.

---

## 🗃️ Database Design

Main tables:

- `users` — accounts and roles
- `issues` — civic reports, location, status, and support count
- `issue_votes` — one support vote per user per issue
- `comments` — public community discussion
- `issue_images` — validated evidence image per issue
- `issue_status_history` — transparent status timeline
- `notifications` — in-app user notifications

---

## 🔐 Security Notes

- Passwords are hashed with Werkzeug password hashing
- CSRF tokens protect POST forms
- Database credentials are read from environment variables
- `.env` is excluded from version control
- Uploaded images are validated and size-limited
- Admin actions require the admin role
- Secure cookie configuration is enabled for production deployments

---

## 🌐 Routes

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

---

## 📊 Admin Dashboard

The admin dashboard provides:

- Total reports
- Not Opened / Open / In Progress / Resolved counts
- Registered users
- Comment counts
- Category breakdown
- Status breakdown
- Monthly report trends
- Recent reports

Charts are rendered with **Chart.js**.

---

## 🔗 Project Links

**Live Application:**  
https://civicsense-hm6y.onrender.com/issues

**GitHub Repository:**  
https://github.com/souravkeshri-14/civicsense

**Deployment Platform:**  
Render

**Database Platform:**  
Aiven MySQL

---

## 👨‍💻 Author

**Sourav Keshri**

GitHub:  
https://github.com/souravkeshri-14

---

## ⭐ Support

If you find CIVICSENSE useful, consider giving the repository a **star ⭐** on GitHub.
