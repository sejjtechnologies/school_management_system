import os, sys
sys.path.insert(0, os.getcwd())
from app import app
from sqlalchemy import text

with app.app_context():
    from models.user_models import db
    try:
        sql = "SELECT setval(pg_get_serial_sequence('roles','id'), COALESCE((SELECT MAX(id) FROM roles), 1), true)"
        db.session.execute(text(sql))
        db.session.commit()
        print("✅ roles.id sequence adjusted successfully")
    except Exception as e:
        db.session.rollback()
        print("❌ Failed to adjust roles sequence:", e)
        raise
