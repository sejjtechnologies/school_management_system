Migration notes for Attendance feature

1. Overview

   This project includes Alembic configuration and an initial migration that creates the
   `attendance` and `attendance_log` tables needed by the new attendance feature.

2. Applying migrations (PowerShell)

   # Set DATABASE_URL if not already in your environment (temporary for the session)
   $env:DATABASE_URL = 'postgresql://user:pass@host:5432/dbname'

   # Run migrations (script will read .env if you pass -UseEnvFile)
   ./scripts/apply_migrations.ps1 -UseEnvFile

   # Or run alembic directly
   python -m alembic upgrade head

3. Quick alternative

   If you prefer to create tables directly via SQLAlchemy (not recommended for production), run:

   python scripts/create_tables.py

4. Troubleshooting

   - Ensure `DATABASE_URL` points to your PostgreSQL instance.
   - Back up your DB before running migrations.
   - If alembic reports errors about imports, run from the project root (where alembic.ini is located).
