import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, session, redirect, url_for, flash, request, send_from_directory
from models.user_models import db, AdminSession
from models import marks_model   # ✅ Import marks_model to include new tables
from routes.user_routes import user_routes
from routes.admin_routes import admin_routes
from routes.secretary_routes import secretary_routes
from routes.teacher_routes import teacher_routes   # ✅ Import teacher_routes
from routes.teacher_manage_reports import teacher_manage_reports   # ✅ Import teacher_manage_reports
from routes.reset_password import reset_password_routes  # ✅ Import reset password routes
from routes.bursar_routes import bursar_routes   # ✅ Import bursar_routes
from routes.parent_routes import parent_routes   # ✅ Import parent_routes
from routes.headteacher_routes import headteacher_routes  # ✅ Import headteacher_routes
from dotenv import load_dotenv   # ✅ Import dotenv
from sqlalchemy import text
from werkzeug.exceptions import MethodNotAllowed

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

# ✅ Configure UTF-8 charset for all responses and templates
app.config['JSON_AS_ASCII'] = False  # Allow non-ASCII characters in JSON responses
# Ensure Jinja2 template loading uses UTF-8
import jinja2
loader = jinja2.FileSystemLoader('templates', encoding='utf-8')
app.jinja_loader = loader

# Remember-me session lifetime (in days). When `session.permanent = True` is set
# for a user (e.g., the "Remember me" checkbox), Flask will set the session cookie
# to expire after this duration. You can override via REMEMBER_DAYS environment var.
remember_days = int(os.getenv('REMEMBER_DAYS', '30'))
app.permanent_session_lifetime = timedelta(days=remember_days)

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
app.register_blueprint(parent_routes)             # ✅ Register parent_routes
app.register_blueprint(headteacher_routes)        # ✅ Register headteacher_routes


# Inject system settings into all templates so dashboards can show maintenance/backup banners
@app.context_processor
def inject_system_settings():
    try:
        from models.system_settings import SystemSettings
        settings = SystemSettings.get_settings()
        last = settings.last_backup_time.strftime('%d/%m/%Y %I:%M:%S %p') if settings.last_backup_time else None
        nxt = settings.next_scheduled_backup.strftime('%d/%m/%Y %I:%M:%S %p') if settings.next_scheduled_backup else None
        # Pop any transient 'welcome back' flag from session so it only appears once
        welcome = False
        try:
            welcome = bool(session.pop('welcome_back', False))
        except Exception:
            welcome = False

        return {
            'system_settings': {
                'maintenance_mode': bool(settings.maintenance_mode),
                'maintenance_message': settings.maintenance_message,
                'auto_backup_enabled': bool(settings.auto_backup_enabled),
                'backup_schedule': settings.backup_schedule,
                'last_backup_time': last,
                'next_scheduled_backup': nxt
            },
            'welcome_back': welcome
        }
    except Exception as e:
        logger.debug(f"Could not inject system_settings: {e}")
        return {}

# ✅ RESPONSE UTF-8 CHARSET MIDDLEWARE
@app.after_request
def ensure_utf8_charset(response):
    """Ensure all text responses include UTF-8 charset in Content-Type header."""
    content_type = response.headers.get('Content-Type', '')

    # ONLY modify text/html responses - leave everything else alone
    # This ensures binary files (gzip, pdf, etc.) are NOT affected
    if content_type.startswith('text/html'):
        if 'charset' not in content_type:
            response.headers['Content-Type'] = 'text/html; charset=utf-8'

    # Don't touch any other content types (binary files, JSON, etc.)

    # ✅ Cleanup: Remove any pending database session to prevent connection pool leaks
    try:
        db.session.remove()
    except Exception as e:
        logger.warning(f"[SESSION CLEANUP] Could not remove session: {str(e)}")

    return response

# ✅ ADMIN SESSION VALIDATION MIDDLEWARE
@app.before_request
def validate_admin_session():
    """Validate that admin sessions are still active. Logout if session was invalidated elsewhere."""
    try:
        # ✅ Skip validation for API endpoints and login/logout pages
        if request.path.startswith('/api/') or request.path in ['/login', '/logout', '/']:
            return
        # ✅ Skip validation for backup progress endpoints (they need to work in background)
        if request.path.startswith('/admin/backup-maintenance/backup-progress') or request.path.startswith('/admin/backup-maintenance/trigger'):
            return

        user_id = session.get("user_id")
        role = session.get("role")
        client_session_id = session.get("active_session_id")  # ✅ Client's session ID from cookie

        # Only check for admin sessions
        if role and role.lower() == "admin" and user_id:
            from models.user_models import User

            # If client doesn't have a session ID, they must log in again
            if not client_session_id:
                print("[DEBUG] Admin has no active_session_id in Flask session, forcing re-login")
                session.clear()
                flash("Your admin session expired. Please log in again.", "danger")
                return redirect(url_for("user_routes.login"))

            # Get user from DB
            user = User.query.get(user_id)
            if not user:
                session.clear()
                flash("Your account was deleted or is no longer available.", "danger")
                return redirect(url_for("user_routes.login"))

            # ✅ KEY CHECK: Compare client's session ID with DB's active session ID
            # If they don't match, this device is no longer the active session
            if user.active_session_id != client_session_id:
                print(f"[SESSION CONFLICT] User {user_id}: Client has {client_session_id[:15]}..., DB has {user.active_session_id[:15] if user.active_session_id else 'None'}...")
                session.clear()
                flash("Your admin session was invalidated. You logged in from another device.", "danger")
                return redirect(url_for("user_routes.login"))

            # ✅ Session IDs match, check if the session is still marked active in DB
            admin_session = AdminSession.query.filter_by(
                session_id=client_session_id,
                user_id=user_id
            ).first()

            if not admin_session or not admin_session.is_active:
                print(f"[SESSION INACTIVE] User {user_id} session is inactive in DB")
                session.clear()
                flash("Your admin session was invalidated. Please log in again.", "danger")
                return redirect(url_for("user_routes.login"))

            # Update last activity timestamp
            admin_session.last_activity = datetime.utcnow()
            db.session.commit()
            print(f"[SESSION VALID] User {user_id} session is active, updated last_activity")
    except Exception as e:
        # Log the error but don't break the request - fail gracefully for Vercel
        logger.error(f"[SESSION VALIDATION ERROR] {str(e)}")
        print(f"[SESSION VALIDATION ERROR] {str(e)}")


# Enforce maintenance mode: if maintenance is active, show a minimal maintenance
# page on user dashboards (teacher, parent, secretary, headteacher, bursar),
# but allow admin users to access the admin dashboard normally.
@app.before_request
def enforce_maintenance_mode():
    try:
        # Skip static and admin endpoints and API endpoints
        path = request.path or ''
        if path.startswith('/static') or path.startswith('/sw.js') or path.startswith('/api'):
            return

        # If the admin dashboard or admin routes are requested, allow (admins should still access)
        if path.startswith('/admin'):
            return

        from models.system_settings import SystemSettings
        settings = SystemSettings.get_settings()
        if not settings or not settings.maintenance_mode:
            return

        # Dashboard paths to intercept when maintenance is active
        maintenance_paths = [
            '/teacher/dashboard',
            '/parent/dashboard',
            '/secretary/dashboard',
            '/headteacher/dashboard',
            '/bursar/dashboard',
        ]

        # If request.path starts with one of the dashboard routes, and the user is not admin,
        # render the maintenance page.
        if any(path.startswith(p) for p in maintenance_paths):
            role = session.get('role', '').lower() if session.get('role') else None
            if role != 'admin':
                message = settings.maintenance_message or 'Maintenance mode: System is under maintenance. Please try again later.'
                return render_template('maintenance.html', message=message), 503
    except Exception as e:
        logger.exception(f"Error enforcing maintenance mode: {e}")
        return

# ✅ GLOBAL ERROR HANDLER for aborted transactions
@app.errorhandler(Exception)
def handle_db_error(error):
    """Catch database transaction errors and rollback."""
    from sqlalchemy.exc import InternalError

    if isinstance(error, InternalError) and "InFailedSqlTransaction" in str(error):
        logger.error(f"[DB TRANSACTION ERROR] Transaction aborted, rolling back: {str(error)}")
        try:
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"[DB ROLLBACK ERROR] Failed to rollback: {str(rollback_error)}")

        # Re-raise the error so Flask can handle it normally
        raise error

    # Let Flask handle other errors normally
    raise error

@app.route("/")
def index():
    logger.info("Index route accessed")
    return render_template("index.html")


# Serve service worker at the root so it can control the entire scope
@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')


# Serve offline fallback at root path for the service worker
@app.route('/offline.html')
def offline_page():
    return send_from_directory('static', 'offline.html')

# ✅ Developer page route
@app.route("/developer")
def developer():
    logger.info("Developer route accessed")
    return render_template("developer.html")


# Provide a helpful handler for MethodNotAllowed (405) so we log the request method/path
# and return a friendly message instead of the default Werkzeug HTML traceback.
@app.errorhandler(MethodNotAllowed)
def handle_method_not_allowed(error):
    try:
        logger.warning(f"MethodNotAllowed: {request.method} {request.path} - {error}")
    except Exception:
        logger.warning(f"MethodNotAllowed error: {error}")
    # Return a concise JSON response for API clients; for browsers, Flask will still render JSON
    return ("Method Not Allowed", 405)


# Generic OPTIONS handler to gracefully respond to preflight requests.
# This helps avoid 405 responses for CORS preflight when clients issue requests
# with custom headers. It intentionally returns permissive headers; restrict
# in production as appropriate.
@app.route('/<path:unused>', methods=['OPTIONS'])
@app.route('/', methods=['OPTIONS'])
def handle_options(unused=None):
    from flask import make_response
    resp = make_response("")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return resp

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
