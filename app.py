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

        # ✅ Auto-generate timetables for all classes/streams on first startup
        from models.class_model import Class
        from models.stream_model import Stream
        from models.timetable_model import TimeTableSlot
        from models.marks_model import Subject
        from datetime import datetime, timedelta
        from models.user_models import User

        # Check if timetables already exist
        existing_slots = TimeTableSlot.query.first()

        if not existing_slots:
            logger.info("Generating timetables for all classes and streams...")
            try:
                # Get ALL teachers (users with role='teacher')
                all_teachers = User.query.filter_by(role='teacher').all()
                if not all_teachers:
                    logger.warning("No teachers found in the system")
                else:
                    logger.info(f"Found {len(all_teachers)} teachers for timetable generation")

                # Get all subjects
                all_subjects = Subject.query.all()
                if not all_subjects:
                    logger.warning("No subjects found, creating default subject")
                    default_subject = Subject(name="General")
                    db.session.add(default_subject)
                    db.session.commit()
                    all_subjects = [default_subject]

                classes = Class.query.all()
                days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

                for class_obj in classes:
                    streams = class_obj.streams
                    if not streams:
                        logger.warning(f"Class {class_obj.name} has no streams, skipping")
                        continue

                    for stream in streams:
                        logger.info(f"Generating timetable for {class_obj.name} - {stream.name}")

                        # Generate time slots for this stream
                        teacher_idx = 0
                        subject_idx = 0
                        current = datetime.strptime("08:00", '%H:%M')
                        end_time = datetime.strptime("17:00", '%H:%M')

                        for day in days_of_week:
                            current = datetime.strptime("08:00", '%H:%M')

                            while current < end_time:
                                time_str = current.strftime('%H:%M')

                                # Skip break time (10:00-10:20)
                                if time_str == '10:00':
                                    current += timedelta(minutes=20)
                                    continue

                                # Skip lunch time (13:00-13:40)
                                if time_str == '13:00':
                                    current += timedelta(minutes=40)
                                    continue

                                # Calculate lesson duration
                                remaining = (end_time - current).total_seconds() / 60
                                duration = 40 if remaining > 40 else int(remaining)

                                if duration <= 0:
                                    break

                                # Distribute ALL teachers round-robin across slots
                                teacher = all_teachers[teacher_idx % len(all_teachers)]

                                # Assign different subjects per stream (rotate subjects)
                                subject = all_subjects[subject_idx % len(all_subjects)]

                                # Create slot
                                end_str = (current + timedelta(minutes=duration)).strftime('%H:%M')

                                slot = TimeTableSlot(
                                    class_id=class_obj.id,
                                    stream_id=stream.id,
                                    teacher_id=teacher.id,
                                    subject_id=subject.id,
                                    day_of_week=day,
                                    start_time=time_str,
                                    end_time=end_str
                                )

                                try:
                                    db.session.add(slot)
                                    db.session.commit()
                                except Exception as e:
                                    db.session.rollback()
                                    logger.warning(f"Could not add slot for {class_obj.name}-{stream.name} {day} {time_str}: {str(e)}")

                                current += timedelta(minutes=duration)
                                teacher_idx += 1
                                subject_idx += 1

                logger.info("✓ Timetables generated successfully for all classes and streams!")
            except Exception as e:
                logger.error(f"Error generating timetables: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")

# ✅ Flask CLI command to regenerate timetables
@app.cli.command()
def generate_timetables():
    """Regenerate timetables for all classes and streams using all teachers."""
    with app.app_context():
        from models.class_model import Class
        from models.stream_model import Stream
        from models.timetable_model import TimeTableSlot
        from models.marks_model import Subject
        from models.user_models import User
        from datetime import datetime, timedelta

        try:
            # Clear existing timetables
            TimeTableSlot.query.delete()
            db.session.commit()
            logger.info("Cleared existing timetables")

            # Get ALL teachers (users with role='teacher')
            all_teachers = User.query.filter_by(role='teacher').all()
            if not all_teachers:
                logger.error("No teachers found in the system")
                print("❌ Error: No teachers found in the system")
                return

            logger.info(f"Found {len(all_teachers)} teachers for timetable generation")
            print(f"✓ Found {len(all_teachers)} teachers")

            # Get all subjects
            all_subjects = Subject.query.all()
            if not all_subjects:
                logger.warning("No subjects found, creating default subject")
                default_subject = Subject(name="General")
                db.session.add(default_subject)
                db.session.commit()
                all_subjects = [default_subject]

            classes = Class.query.all()
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

            total_slots = 0

            for class_obj in classes:
                streams = class_obj.streams
                if not streams:
                    logger.warning(f"Class {class_obj.name} has no streams, skipping")
                    continue

                for stream in streams:
                    logger.info(f"Generating timetable for {class_obj.name} - {stream.name}")

                    teacher_idx = 0
                    subject_idx = 0
                    current = datetime.strptime("08:00", '%H:%M')
                    end_time = datetime.strptime("17:00", '%H:%M')

                    for day in days_of_week:
                        current = datetime.strptime("08:00", '%H:%M')

                        while current < end_time:
                            time_str = current.strftime('%H:%M')

                            # Skip break time (10:00-10:20)
                            if time_str == '10:00':
                                current += timedelta(minutes=20)
                                continue

                            # Skip lunch time (13:00-13:40)
                            if time_str == '13:00':
                                current += timedelta(minutes=40)
                                continue

                            # Calculate lesson duration
                            remaining = (end_time - current).total_seconds() / 60
                            duration = 40 if remaining > 40 else int(remaining)

                            if duration <= 0:
                                break

                            # Distribute ALL teachers round-robin
                            teacher = all_teachers[teacher_idx % len(all_teachers)]

                            # Assign different subjects per stream (rotate subjects)
                            subject = all_subjects[subject_idx % len(all_subjects)]

                            # Create slot
                            end_str = (current + timedelta(minutes=duration)).strftime('%H:%M')

                            slot = TimeTableSlot(
                                class_id=class_obj.id,
                                stream_id=stream.id,
                                teacher_id=teacher.id,
                                subject_id=subject.id,
                                day_of_week=day,
                                start_time=time_str,
                                end_time=end_str
                            )

                            db.session.add(slot)
                            current += timedelta(minutes=duration)
                            teacher_idx += 1
                            subject_idx += 1
                            total_slots += 1

                    db.session.commit()

            logger.info(f"✓ Timetables regenerated successfully! ({total_slots} total slots)")
            print(f"✓ Timetables regenerated successfully! ({total_slots} total slots)")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error regenerating timetables: {str(e)}")
            print(f"❌ Error: {str(e)}")

# ✅ Entry point for local testing
if __name__ == "__main__":
    logger.info("Starting Flask app locally...")
    app.run(debug=True)
