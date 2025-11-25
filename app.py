import os
import logging
from flask import Flask, render_template
from models.user_models import db
from models import marks_model   # ✅ Import marks_model to include new tables
from routes.user_routes import user_routes
from routes.admin_routes import admin_routes
from routes.secretary_routes import secretary_routes
from routes.teacher_routes import teacher_routes   # ✅ Import teacher_routes
from routes.teacher_manage_reports import teacher_manage_reports   # ✅ Import teacher_manage_reports
from dotenv import load_dotenv   # ✅ Import dotenv
from sqlalchemy import text       # ✅ Import text for SQL execution

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

# ✅ Initialize DB
db.init_app(app)

# ✅ Register Blueprints
app.register_blueprint(user_routes)
app.register_blueprint(admin_routes)
app.register_blueprint(secretary_routes)
app.register_blueprint(teacher_routes)            # ✅ Register teacher_routes
app.register_blueprint(teacher_manage_reports)    # ✅ Register teacher_manage_reports

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

# ✅ Auto-create tables if missing
with app.app_context():
    try:
        db.create_all()  # ✅ This now includes marks_model tables
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")

# ✅ Entry point for local testing
if __name__ == "__main__":
    logger.info("Starting Flask app locally...")
    app.run(debug=True)