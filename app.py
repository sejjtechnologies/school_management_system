import os
import logging
from datetime import datetime
from flask import Flask, render_template, session, redirect, url_for, flash
from models.user_models import db, AdminSession
from models import marks_model   # ✅ Import marks_model to include new tables
from routes.user_routes import user_routes
from routes.admin_routes import admin_routes
from routes.secretary_routes import secretary_routes
from routes.teacher_routes import teacher_routes   # ✅ Import teacher_routes
from routes.teacher_manage_reports import teacher_manage_reports   # ✅ Import teacher_manage_reports
from routes.reset_password import reset_password_routes  # ✅ Import reset password routes
from routes.bursar_routes import bursar_routes   # ✅ Import bursar_routes
from dotenv import load_dotenv   # ✅ Import dotenv
from sqlalchemy import text

# ✅ Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# ✅ Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Log everything (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ✅ Secret key from environment
app.secret_key = os.getenv("SECRET_KEY", "default_secret")

# ✅ Database configuration from environment
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = (
    os.getenv("SQLALCHEMY_TRACK_MODIFICATIONS", "False") == "True"
)

# ✅ Configure SQLAlchemy engine options to handle SSL/Neon connections
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,  # ✅ Prevent "SSL connection has been closed unexpectedly"
    "pool_size": 5,
    "max_overflow": 10,
    "pool_recycle": 1800  # Optional: recycle connections every 30 minutes
}

# ✅ Initialize DB
db.init_app(app)

# ✅ Register Blueprints
app.register_blueprint(user_routes)
app.register_blueprint(admin_routes)
app.register_blueprint(secretary_routes)
app.register_blueprint(teacher_routes)            # ✅ Register teacher_routes
app.register_blueprint(teacher_manage_reports)    # ✅ Register teacher_manage_reports
app.register_blueprint(reset_password_routes)     # ✅ Register reset password routes
app.register_blueprint(bursar_routes, url_prefix="/bursar")  # ✅ Register bursar_routes

# ✅ ADMIN SESSION VALIDATION MIDDLEWARE
@app.before_request
def validate_admin_session():
    """Validate that admin sessions are still active. Logout if session was invalidated elsewhere."""
    user_id = session.get("user_id")
    role = session.get("role")
    
    # Only check for admin sessions
    if role and role.lower() == "admin" and user_id:
        from models.user_models import User
        
        # Always check the database for the current user's active session
        user = User.query.get(user_id)
        if not user:
            # User no longer exists, logout
            session.clear()
            flash("Your account was deleted or is no longer available.", "danger")
            return redirect(url_for("user_routes.login"))
        
        # Check if this admin has an active session in the database
        if not user.active_session_id:
            # No active session in DB, force logout
            print(f"[⚠️ ADMIN SESSION INVALID] User {user_id} has no active session in DB")
            session.clear()
            flash("Your admin session is no longer valid. Please log in again.", "danger")
            return redirect(url_for("user_routes.login"))
        
        # Check if the active session exists and is active
        admin_session = AdminSession.query.filter_by(
            session_id=user.active_session_id,
            user_id=user_id
        ).first()
        
        if not admin_session or not admin_session.is_active:
            # Session was invalidated (logged in from another device)
            print(f"[⚠️ ADMIN SESSION INVALIDATED] User {user_id} attempted access with inactive session")
            session.clear()
            flash("Your admin session was invalidated. You logged in from another device.", "danger")
            return redirect(url_for("user_routes.login"))
        
        # Update last activity timestamp
        admin_session.last_activity = datetime.utcnow()
        db.session.commit()

@app.route("/")
def index():
    logger.info("Index route accessed")
    return render_template("index.html")

# ✅ Developer page route
@app.route("/developer")
def developer():
    logger.info("Developer route accessed")
    return render_template("developer.html")

# ✅ Health check route for DB connection
@app.route("/health")
def health():
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return "Database connection OK"
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return f"Database connection failed: {str(e)}"

# ✅ Auto-create tables if missing (generation moved to admin routes)
# NOTE: db.create_all() is commented out due to Neon DB connection pool congestion
# Tables are created by seed scripts or manual migration. Uncomment to enable.
# with app.app_context():
#     try:
#         db.create_all()  # ensures all models' tables exist
#         logger.info("Database tables created successfully (timetable generation moved to admin routes)")
#     except Exception as e:
#         logger.error(f"Error creating tables: {str(e)}")

# ✅ Entry point for local testing
if __name__ == "__main__":
    logger.info("Starting Flask app locally...")
    app.run(debug=True)
