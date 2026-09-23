import os
import hmac
import secrets
from datetime import datetime
from pathlib import Path
from functools import wraps
from io import BytesIO

import pymysql
from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from PIL import Image, UnidentifiedImageError
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv(Path(__file__).resolve().parent / ".env")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "dev-only-secret-change-me"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

SCHEMA_READY = False
USER_PK = "id"
COMMENT_PK = "id"
ALLOWED_STATUS = {"not_opened", "open", "in_progress", "resolved"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 4 * 1024 * 1024


def get_db():
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DB", "civicsense_prod"),
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=10,
        read_timeout=15,
        write_timeout=15,
        charset="utf8mb4",
        ssl={"check_hostname": False},
    )


def column_names(cursor, table):
    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
    return {row["Field"] for row in cursor.fetchall()}


def choose_pk(cursor, table, fallback="id"):
    cursor.execute(f"SHOW KEYS FROM `{table}` WHERE Key_name='PRIMARY'")
    rows = cursor.fetchall()
    return rows[0]["Column_name"] if rows else fallback


def ensure_column(cursor, table, column, definition):
    columns = column_names(cursor, table)
    if column not in columns:
        cursor.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")


def ensure_schema():
    global SCHEMA_READY, USER_PK, COMMENT_PK
    if SCHEMA_READY:
        return

    connection = get_db()
    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(30) DEFAULT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        ensure_column(cursor, "users", "role", "VARCHAR(20) NOT NULL DEFAULT 'user'")
        ensure_column(cursor, "users", "created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        USER_PK = choose_pk(cursor, "users")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                issue_id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                category VARCHAR(100) NOT NULL,
                latitude DECIMAL(10,8) DEFAULT NULL,
                longitude DECIMAL(11,8) DEFAULT NULL,
                location_accuracy DECIMAL(10,2) DEFAULT NULL,
                reported_by INT DEFAULT NULL,
                upvotes INT NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'not_opened',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_issues_category (category),
                INDEX idx_issues_status (status),
                INDEX idx_issues_reporter (reported_by),
                INDEX idx_issues_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        ensure_column(cursor, "issues", "reported_by", "INT DEFAULT NULL")
        ensure_column(cursor, "issues", "upvotes", "INT NOT NULL DEFAULT 0")
        ensure_column(cursor, "issues", "status", "VARCHAR(20) NOT NULL DEFAULT 'not_opened'")
        ensure_column(cursor, "issues", "created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        ensure_column(cursor, "issues", "location_accuracy", "DECIMAL(10,2) DEFAULT NULL")

        # Normalize legacy/blank statuses. New/unreviewed reports start as Not Opened.
        cursor.execute("UPDATE issues SET status='not_opened' WHERE status IS NULL OR TRIM(status)=''")
        cursor.execute("UPDATE issues SET status='in_progress' WHERE LOWER(TRIM(status)) IN ('in progress','in-progress')")
        cursor.execute("UPDATE issues SET status='not_opened' WHERE LOWER(TRIM(status)) NOT IN ('not_opened','open','in_progress','resolved')")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issue_votes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                issue_id INT NOT NULL,
                user_id INT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_issue_user_vote (issue_id, user_id),
                INDEX idx_votes_user (user_id),
                CONSTRAINT fk_votes_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_votes_user FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                issue_id INT NOT NULL,
                user_id INT NOT NULL,
                comment_text VARCHAR(1000) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_comments_issue (issue_id),
                INDEX idx_comments_user (user_id),
                CONSTRAINT fk_comments_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_comments_user FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        ensure_column(cursor, "comments", "created_at", "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP")
        COMMENT_PK = choose_pk(cursor, "comments")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issue_images (
                issue_id INT PRIMARY KEY,
                image_data LONGBLOB NOT NULL,
                mime_type VARCHAR(50) NOT NULL DEFAULT 'image/jpeg',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_issue_images_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS issue_status_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                issue_id INT NOT NULL,
                status VARCHAR(20) NOT NULL,
                changed_by INT DEFAULT NULL,
                note VARCHAR(500) DEFAULT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_status_history_issue (issue_id),
                INDEX idx_status_history_created (created_at),
                CONSTRAINT fk_status_history_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_status_history_user FOREIGN KEY (changed_by) REFERENCES users(id)
                    ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                issue_id INT DEFAULT NULL,
                notification_type VARCHAR(50) NOT NULL DEFAULT 'general',
                title VARCHAR(200) NOT NULL,
                message VARCHAR(500) NOT NULL,
                is_read TINYINT(1) NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_notifications_user (user_id),
                INDEX idx_notifications_unread (user_id, is_read),
                CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_notifications_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        # Backfill initial status history for older records imported before this feature existed.
        cursor.execute(
            """
            INSERT INTO issue_status_history (issue_id, status, changed_by, created_at)
            SELECT i.issue_id, i.status, i.reported_by, i.created_at
            FROM issues i
            WHERE NOT EXISTS (
                SELECT 1 FROM issue_status_history h WHERE h.issue_id = i.issue_id
            )
            """
        )

        # Provision/promote the configured administrator.
        admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
        admin_password = os.environ.get("ADMIN_PASSWORD", "")
        if admin_email and admin_password:
            cursor.execute("SELECT * FROM users WHERE email=%s LIMIT 1", (admin_email,))
            admin = cursor.fetchone()
            if admin:
                cursor.execute("UPDATE users SET role='admin' WHERE email=%s", (admin_email,))
            else:
                cursor.execute(
                    "INSERT INTO users (name, email, password, phone, role) VALUES (%s,%s,%s,%s,'admin')",
                    (
                        "CIVICSENSE Admin",
                        admin_email,
                        generate_password_hash(admin_password),
                        "",
                    ),
                )

        connection.commit()
        SCHEMA_READY = True
    finally:
        connection.close()


def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


@app.before_request
def startup_and_protect():
    if request.endpoint in {"health", "static"}:
        return

    ensure_schema()

    if request.method == "POST":
        incoming = request.form.get("_csrf", "")
        expected = session.get("_csrf", "")
        if not incoming or not expected or not hmac.compare_digest(incoming, expected):
            abort(400, description="Invalid or missing CSRF token.")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            next_url = request.full_path if request.full_path != "//" else url_for("view_issues")
            return redirect(url_for("login", next=next_url))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Administrator access is required for that action.", "danger")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


def authenticate(email, password):
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s LIMIT 1", (email,))
        user = cursor.fetchone()
        if not user:
            return None

        stored = user.get("password", "")
        valid = False
        try:
            valid = check_password_hash(stored, password)
        except (ValueError, TypeError):
            valid = False

        if not valid and stored == password:
            valid = True
            cursor.execute(
                "UPDATE users SET password=%s WHERE email=%s",
                (generate_password_hash(password), email),
            )
            connection.commit()

        return user if valid else None
    finally:
        connection.close()


def user_pk(user):
    return user.get(USER_PK) if USER_PK in user else user.get("id")


def normalize_status(status):
    value = str(status or "").strip().lower().replace("-", "_").replace(" ", "_")
    return value if value in ALLOWED_STATUS else "not_opened"


def process_image(upload):
    if not upload or not upload.filename:
        return None

    raw = upload.read()
    if not raw:
        return None
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 4 MB or smaller.")

    try:
        with Image.open(BytesIO(raw)) as image:
            image.verify()
        with Image.open(BytesIO(raw)) as image:
            image.thumbnail((1600, 1200))
            if image.mode in ("RGBA", "LA"):
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="JPEG", quality=82, optimize=True)
            return output.getvalue(), "image/jpeg"
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Please upload a valid image file.") from exc


def get_issue(cursor, issue_id):
    cursor.execute(
        """
        SELECT i.*, u.name AS reporter_name, u.email AS reporter_email,
               CASE WHEN img.issue_id IS NULL THEN 0 ELSE 1 END AS has_image
        FROM issues i
        LEFT JOIN users u ON i.reported_by = u.id
        LEFT JOIN issue_images img ON img.issue_id = i.issue_id
        WHERE i.issue_id=%s
        """,
        (issue_id,),
    )
    issue = cursor.fetchone()
    if issue:
        issue["status"] = normalize_status(issue.get("status"))
    return issue


def get_comments(cursor, issue_id):
    cursor.execute(
        f"""
        SELECT c.`{COMMENT_PK}` AS comment_id, c.comment_text, c.created_at,
               COALESCE(u.name, u.email, 'Community User') AS user_name
        FROM comments c
        LEFT JOIN users u ON c.user_id = u.`{USER_PK}`
        WHERE c.issue_id=%s
        ORDER BY c.created_at DESC, c.`{COMMENT_PK}` DESC
        """,
        (issue_id,),
    )
    return cursor.fetchall()


def notify_user(cursor, user_id, issue_id, title, message, kind="general"):
    if not user_id:
        return
    cursor.execute(
        """
        INSERT INTO notifications (user_id, issue_id, notification_type, title, message)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (user_id, issue_id, kind, title, message),
    )


@app.context_processor
def global_context():
    unread = 0
    if session.get("user_id"):
        try:
            connection = get_db()
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT COUNT(*) AS n FROM notifications WHERE user_id=%s AND is_read=0",
                    (session["user_id"],),
                )
                unread = int(cursor.fetchone()["n"])
            finally:
                connection.close()
        except Exception:
            unread = 0

    return {
        "current_user": session.get("name"),
        "current_email": session.get("email"),
        "is_logged_in": bool(session.get("user_id")),
        "is_admin": session.get("role") == "admin",
        "unread_notifications": unread,
        "csrf_token": csrf_token,
    }


@app.route("/")
def home():
    return redirect(url_for("view_issues"))


@app.route("/health")
def health():
    return "OK", 200


@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.form.get("next") or request.args.get("next") or url_for("view_issues")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("login.html", next_url=next_url, admin_mode=False)

        user = authenticate(email, password)
        if not user:
            flash("Invalid email or password.", "danger")
            return render_template("login.html", next_url=next_url, admin_mode=False)

        session.clear()
        session["user_id"] = user_pk(user)
        session["name"] = user.get("name") or user.get("email")
        session["email"] = user.get("email")
        session["role"] = user.get("role", "user")
        csrf_token()
        flash("Welcome back!", "success")
        return redirect(next_url if next_url.startswith("/") else url_for("view_issues"))

    return render_template("login.html", next_url=next_url, admin_mode=False)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = authenticate(email, password)
        if not user or user.get("role") != "admin":
            flash("Invalid administrator credentials.", "danger")
            return render_template("login.html", next_url=url_for("admin_dashboard"), admin_mode=True)

        session.clear()
        session["user_id"] = user_pk(user)
        session["name"] = user.get("name") or user.get("email")
        session["email"] = user.get("email")
        session["role"] = "admin"
        csrf_token()
        flash("Administrator login successful.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("login.html", next_url=url_for("admin_dashboard"), admin_mode=True)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()

        if not name or not email or len(password) < 6:
            flash("Name, email, and a password of at least 6 characters are required.", "danger")
            return render_template("register.html")

        connection = get_db()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM users WHERE email=%s LIMIT 1", (email,))
            if cursor.fetchone():
                flash("An account with this email already exists.", "danger")
                return render_template("register.html")
            cursor.execute(
                "INSERT INTO users (name,email,password,phone,role) VALUES (%s,%s,%s,%s,'user')",
                (name, email, generate_password_hash(password), phone),
            )
            connection.commit()
        finally:
            connection.close()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("view_issues"))


@app.route("/report")
@login_required
def report():
    return render_template("report_issue.html")


@app.route("/report_issue", methods=["POST"])
@login_required
def report_issue():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    latitude = request.form.get("latitude") or None
    longitude = request.form.get("longitude") or None
    location_accuracy = request.form.get("location_accuracy") or None

    try:
        if latitude is not None:
            latitude = float(latitude)
        if longitude is not None:
            longitude = float(longitude)
        if location_accuracy is not None:
            location_accuracy = max(0.0, float(location_accuracy))
    except ValueError:
        flash("Invalid location data. Please select your location again.", "danger")
        return redirect(url_for("report"))

    if latitude is not None and not (-90 <= latitude <= 90):
        flash("Invalid latitude.", "danger")
        return redirect(url_for("report"))
    if longitude is not None and not (-180 <= longitude <= 180):
        flash("Invalid longitude.", "danger")
        return redirect(url_for("report"))

    if not title or not description or not category:
        flash("Title, category, and description are required.", "danger")
        return redirect(url_for("report"))

    try:
        processed = process_image(request.files.get("image"))
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("report"))

    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO issues (title, description, category, latitude, longitude, location_accuracy, reported_by, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,'not_opened')
            """,
            (title, description, category, latitude, longitude, location_accuracy, session["user_id"]),
        )
        issue_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO issue_status_history (issue_id,status,changed_by,note) VALUES (%s,'not_opened',%s,%s)",
            (issue_id, session["user_id"], "Issue reported — awaiting admin review"),
        )

        if processed:
            image_data, mime_type = processed
            cursor.execute(
                "INSERT INTO issue_images (issue_id,image_data,mime_type) VALUES (%s,%s,%s)",
                (issue_id, image_data, mime_type),
            )

        connection.commit()
    finally:
        connection.close()

    flash("Your civic issue was reported successfully.", "success")
    return redirect(url_for("issue_detail", issue_id=issue_id))


@app.route("/issues")
def view_issues():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()

    connection = get_db()
    try:
        cursor = connection.cursor()
        conditions = []
        params = []
        if query:
            conditions.append("(i.title LIKE %s OR i.description LIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])
        if category:
            conditions.append("i.category=%s")
            params.append(category)
        if status in ALLOWED_STATUS:
            conditions.append("i.status=%s")
            params.append(status)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        cursor.execute(
            f"""
            SELECT i.*, u.name AS reporter_name,
                   CASE WHEN img.issue_id IS NULL THEN 0 ELSE 1 END AS has_image,
                   (SELECT COUNT(*) FROM comments c WHERE c.issue_id=i.issue_id) AS comment_count
            FROM issues i
            LEFT JOIN users u ON i.reported_by=u.id
            LEFT JOIN issue_images img ON img.issue_id=i.issue_id
            {where}
            ORDER BY i.created_at DESC
            """,
            tuple(params),
        )
        issues = cursor.fetchall()
        for issue in issues:
            issue["status"] = normalize_status(issue.get("status"))

        cursor.execute("SELECT DISTINCT category FROM issues ORDER BY category")
        categories = [r["category"] for r in cursor.fetchall()]

        cursor.execute(
            "SELECT COUNT(*) AS total, SUM(status='not_opened') AS not_opened_count, SUM(status='open') AS open_count, SUM(status='in_progress') AS progress_count, SUM(status='resolved') AS resolved_count FROM issues"
        )
        totals = cursor.fetchone()

        issue_comments = {}
        for issue in issues:
            issue_comments[issue["issue_id"]] = get_comments(cursor, issue["issue_id"])

        # Reuse the issue rows already loaded for the page instead of making
        # a second database request from JavaScript just to populate the map.
        map_issues = []
        for issue in issues:
            if issue.get("latitude") is None or issue.get("longitude") is None:
                continue
            map_issues.append({
                "issue_id": issue["issue_id"],
                "title": issue["title"],
                "category": issue["category"],
                "latitude": float(issue["latitude"]),
                "longitude": float(issue["longitude"]),
                "accuracy": float(issue["location_accuracy"]) if issue.get("location_accuracy") is not None else None,
                "status": normalize_status(issue.get("status")),
                "upvotes": int(issue.get("upvotes") or 0),
                "created_at": issue["created_at"].isoformat() if issue.get("created_at") else "",
            })

        return render_template(
            "view_issues.html",
            issues=issues,
            issue_comments=issue_comments,
            map_issues=map_issues,
            categories=categories,
            totals=totals,
            filters={"q": query, "category": category, "status": status},
        )
    finally:
        connection.close()


@app.route("/issue/<int:issue_id>")
def issue_detail(issue_id):
    connection = get_db()
    try:
        cursor = connection.cursor()
        issue = get_issue(cursor, issue_id)
        if not issue:
            abort(404)
        comments = get_comments(cursor, issue_id)
        cursor.execute(
            """
            SELECT h.status, h.note, h.created_at, COALESCE(u.name, 'System') AS changed_by_name
            FROM issue_status_history h
            LEFT JOIN users u ON h.changed_by=u.id
            WHERE h.issue_id=%s
            ORDER BY h.created_at DESC, h.id DESC
            """,
            (issue_id,),
        )
        status_history = cursor.fetchall()
        return render_template(
            "issue_detail.html",
            issue=issue,
            comments=comments,
            status_history=status_history,
        )
    finally:
        connection.close()


@app.route("/issues/<int:issue_id>/image")
def issue_image(issue_id):
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT image_data,mime_type FROM issue_images WHERE issue_id=%s", (issue_id,))
        image = cursor.fetchone()
        if not image:
            abort(404)
        return send_file(BytesIO(image["image_data"]), mimetype=image["mime_type"], download_name=f"civicsense-{issue_id}.jpg")
    finally:
        connection.close()


@app.route("/map")
def map_view():
    return render_template("map.html")


@app.route("/api/issues")
def issues_api():
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT issue_id,title,category,latitude,longitude,location_accuracy,status,upvotes,created_at
            FROM issues
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            ORDER BY created_at DESC
            """
        )
        rows = cursor.fetchall()
        payload = []
        for row in rows:
            payload.append(
                {
                    "issue_id": row["issue_id"],
                    "title": row["title"],
                    "category": row["category"],
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "accuracy": float(row["location_accuracy"]) if row.get("location_accuracy") is not None else None,
                    "status": normalize_status(row["status"]),
                    "upvotes": int(row["upvotes"] or 0),
                    "created_at": row["created_at"].isoformat() if row["created_at"] else "",
                }
            )
        return jsonify(payload)
    finally:
        connection.close()


@app.route("/upvote/<int:issue_id>", methods=["POST"])
@login_required
def upvote(issue_id):
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM issue_votes WHERE issue_id=%s AND user_id=%s LIMIT 1", (issue_id, session["user_id"]))
        if cursor.fetchone():
            flash("You have already supported this issue.", "warning")
        else:
            cursor.execute("INSERT INTO issue_votes (issue_id,user_id) VALUES (%s,%s)", (issue_id, session["user_id"]))
            cursor.execute("UPDATE issues SET upvotes=COALESCE(upvotes,0)+1 WHERE issue_id=%s", (issue_id,))
            flash("Your support was added.", "success")
        connection.commit()
    finally:
        connection.close()
    return redirect(request.referrer or url_for("view_issues"))


@app.route("/comment/<int:issue_id>", methods=["POST"])
@login_required
def comment(issue_id):
    text = request.form.get("comment", "").strip()
    if not text:
        flash("Comment cannot be empty.", "danger")
        return redirect(request.referrer or url_for("issue_detail", issue_id=issue_id))
    if len(text) > 1000:
        flash("Comment is too long.", "danger")
        return redirect(request.referrer or url_for("issue_detail", issue_id=issue_id))

    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT reported_by,title FROM issues WHERE issue_id=%s", (issue_id,))
        issue = cursor.fetchone()
        if not issue:
            abort(404)

        cursor.execute(
            "INSERT INTO comments (issue_id,user_id,comment_text) VALUES (%s,%s,%s)",
            (issue_id, session["user_id"], text),
        )
        if issue["reported_by"] and issue["reported_by"] != session["user_id"]:
            notify_user(
                cursor,
                issue["reported_by"],
                issue_id,
                "New comment on your report",
                f"Someone commented on your issue: {issue['title']}",
                "comment",
            )
        connection.commit()
    finally:
        connection.close()

    flash("Comment added. Everyone can now see it.", "success")
    return redirect(request.referrer or url_for("issue_detail", issue_id=issue_id))


@app.route("/notifications")
@login_required
def notifications():
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 100",
            (session["user_id"],),
        )
        rows = cursor.fetchall()
        return render_template("notifications.html", notifications=rows)
    finally:
        connection.close()


@app.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def notification_read(notification_id):
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE notifications SET is_read=1 WHERE id=%s AND user_id=%s",
            (notification_id, session["user_id"]),
        )
        connection.commit()
    finally:
        connection.close()
    return redirect(request.referrer or url_for("notifications"))


@app.route("/notifications/read-all", methods=["POST"])
@login_required
def notifications_read_all():
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session["user_id"],))
        connection.commit()
    finally:
        connection.close()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("notifications"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) total FROM issues")
        total_issues = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) total FROM users")
        total_users = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) total FROM comments")
        total_comments = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) total FROM issues WHERE status='resolved'")
        total_resolved = cursor.fetchone()["total"]

        cursor.execute("SELECT category, COUNT(*) total FROM issues GROUP BY category ORDER BY total DESC")
        by_category = cursor.fetchall()
        cursor.execute("SELECT status, COUNT(*) total FROM issues GROUP BY status")
        by_status = cursor.fetchall()
        cursor.execute(
            """
            SELECT DATE_FORMAT(created_at,'%Y-%m') month, COUNT(*) total
            FROM issues
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 5 MONTH)
            GROUP BY DATE_FORMAT(created_at,'%Y-%m')
            ORDER BY month
            """
        )
        by_month = cursor.fetchall()
        cursor.execute(
            """
            SELECT i.issue_id,i.title,i.category,i.status,i.upvotes,i.created_at,
                   COALESCE(u.name,'Anonymous') reporter_name
            FROM issues i
            LEFT JOIN users u ON i.reported_by=u.id
            ORDER BY i.created_at DESC
            LIMIT 8
            """
        )
        recent = cursor.fetchall()

        return render_template(
            "admin_dashboard.html",
            metrics={
                "issues": total_issues,
                "users": total_users,
                "comments": total_comments,
                "resolved": total_resolved,
            },
            by_category=by_category,
            by_status=by_status,
            by_month=by_month,
            recent=recent,
        )
    finally:
        connection.close()


@app.route("/admin/issue/<int:issue_id>/status", methods=["POST"])
@admin_required
def update_issue_status(issue_id):
    status = request.form.get("status", "").strip()
    note = request.form.get("note", "").strip()[:500]
    if status not in ALLOWED_STATUS:
        flash("Invalid issue status.", "danger")
        return redirect(request.referrer or url_for("view_issues"))

    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT status,reported_by,title FROM issues WHERE issue_id=%s", (issue_id,))
        issue = cursor.fetchone()
        if not issue:
            abort(404)

        old_status = normalize_status(issue["status"])
        if old_status == status and not note:
            flash("No status change was made.", "warning")
            return redirect(request.referrer or url_for("issue_detail", issue_id=issue_id))

        cursor.execute("UPDATE issues SET status=%s WHERE issue_id=%s", (status, issue_id))
        cursor.execute(
            "INSERT INTO issue_status_history (issue_id,status,changed_by,note) VALUES (%s,%s,%s,%s)",
            (issue_id, status, session["user_id"], note or None),
        )

        if issue["reported_by"] and issue["reported_by"] != session["user_id"]:
            label = {"not_opened": "Not Opened", "open": "Open", "in_progress": "In Progress", "resolved": "Resolved"}[status]
            message = f'Your issue "{issue["title"]}" is now {label}.'
            if note:
                message += f" Note: {note}"
            notify_user(cursor, issue["reported_by"], issue_id, "Issue status updated", message, "status_change")

        connection.commit()
    finally:
        connection.close()

    flash("Issue status and history updated.", "success")
    return redirect(request.referrer or url_for("issue_detail", issue_id=issue_id))


@app.route("/admin/issue/<int:issue_id>/delete", methods=["POST"])
@admin_required
def delete_issue(issue_id):
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM issue_status_history WHERE issue_id=%s", (issue_id,))
        cursor.execute("DELETE FROM issue_images WHERE issue_id=%s", (issue_id,))
        cursor.execute("DELETE FROM notifications WHERE issue_id=%s", (issue_id,))
        cursor.execute("DELETE FROM issue_votes WHERE issue_id=%s", (issue_id,))
        cursor.execute("DELETE FROM comments WHERE issue_id=%s", (issue_id,))
        cursor.execute("DELETE FROM issues WHERE issue_id=%s", (issue_id,))
        connection.commit()
    finally:
        connection.close()

    flash("Issue deleted.", "success")
    return redirect(url_for("view_issues"))


@app.route("/admin/comment/<int:comment_id>/delete", methods=["POST"])
@admin_required
def delete_comment(comment_id):
    connection = get_db()
    try:
        cursor = connection.cursor()
        cursor.execute(f"DELETE FROM comments WHERE `{COMMENT_PK}`=%s", (comment_id,))
        connection.commit()
    finally:
        connection.close()

    flash("Comment deleted.", "success")
    return redirect(request.referrer or url_for("view_issues"))


@app.errorhandler(413)
def file_too_large(_error):
    flash("Uploaded file is too large. Maximum upload size is 5 MB.", "danger")
    return redirect(url_for("report")), 413


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
