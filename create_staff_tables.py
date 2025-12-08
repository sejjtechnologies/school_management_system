"""
Create Staff-related tables in the database.

This script loads environment variables from a .env file, connects to your
Neon/Postgres database via SQLAlchemy, imports the new staff models and
creates the tables.

Usage:
  python create_staff_tables.py

Environment variables (in .env):
  DATABASE_URL (Postgres-style URL, e.g. postgres://user:pass@host:port/dbname)

Note: this script uses the project's shared SQLAlchemy `db` instance defined
in `models/user_models.py` and imports model modules under `models/` so their
metadata is registered before calling `db.create_all()`.
"""

import os
from dotenv import load_dotenv
from flask import Flask

# load .env from repo root
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('NEON_DATABASE_URL')
if not DATABASE_URL:
    print('ERROR: DATABASE_URL (or NEON_DATABASE_URL) not set in environment or .env')
    raise SystemExit(1)


def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Optional: tune pool size/timeouts for Neon if desired
    return app


def main():
    app = create_app()

    # Import db and initialize
    from models.user_models import db

    db.init_app(app)

    # Import the staff models so they are registered with SQLAlchemy metadata
    # and also import other models that may be referenced by foreign keys.
    import models.staff_models  # newly added
    import models.user_models
    import models.salary_models
    import models.register_pupils

    with app.app_context():
        print('Creating staff-related tables...')
        db.create_all()
        print('Done. Tables created (if not existing).')


if __name__ == '__main__':
    main()
