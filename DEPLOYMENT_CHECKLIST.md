# CIVICSENSE Deployment Checklist

## Local

1. Create a virtual environment.
2. Run `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Fill in MySQL/Aiven credentials and admin credentials.
5. Run `python app.py`.
6. Test:
   - `/health`
   - `/issues`
   - `/map`
   - `/register` and `/login`
   - `/report`
   - `/admin/login`
   - `/admin/dashboard`
   - `/notifications`
7. Confirm an issue can be reported with a photo and GPS location.
8. Confirm admin status update creates history and a notification.
9. Confirm comments are readable while logged out and posting requires login.
10. Confirm dark mode works.

## GitHub

1. Keep `.env` out of Git.
2. Keep `.venv`, `.idea`, caches and logs out of Git.
3. Commit the project files and push to the repository.

## Render

1. Create a Web Service from the GitHub repository.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Health check: `/health`
5. Add environment variables:
   - `MYSQL_HOST`
   - `MYSQL_PORT`
   - `MYSQL_USER`
   - `MYSQL_PASSWORD`
   - `MYSQL_DB`
   - `SECRET_KEY`
   - `COOKIE_SECURE=1`
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`
6. Deploy.
7. Open the live site and repeat the local test checklist.

## Existing Aiven database

The application automatically creates the new tables and adds the missing `issues.reported_by` and auth columns on startup. `migrate_existing.sql` is also included for manual migration.

## Important

Never commit real passwords, `.env`, database dumps, or private API credentials.

Never commit the real Aiven password or admin password. Use placeholders in `.env.example` and set real values locally/inside Render Environment Variables.
Use placeholder values such as `your-aiven-password` in examples; never store real passwords here.
