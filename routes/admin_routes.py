from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from models.user_models import db, User, Role
from models.system_settings import SystemSettings
from sqlalchemy import func
from models.class_model import Class
from models.stream_model import Stream
from models.marks_model import Subject
from models.teacher_assignment_models import TeacherAssignment
from models.timetable_model import TimeTableSlot
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import threading
import uuid
import time
import json
import os
try:
    import redis
except Exception:
    redis = None


# Helper: check whether a teacher has an overlapping slot
def teacher_has_overlap(teacher_id, day_of_week, start_time, end_time,
                        exclude_slot_id=None, exclude_class_id=None, exclude_stream_id=None):
    """Return True if the teacher has any timetable slot on the given day that overlaps
    the interval [start_time, end_time). Times are 'HH:MM' strings.

    Optional excludes:
      - exclude_slot_id: ignore a specific slot (useful during updates).
      - exclude_class_id / exclude_stream_id: ignore all slots belonging to a
        particular class+stream (useful during generation when we are replacing
        slots for the same class/stream).
    """
    query = TimeTableSlot.query.filter(
        TimeTableSlot.teacher_id == teacher_id,
        TimeTableSlot.day_of_week == day_of_week,
    )

    if exclude_slot_id:
        query = query.filter(TimeTableSlot.id != exclude_slot_id)

    if exclude_class_id is not None and exclude_stream_id is not None:
        # Exclude slots that belong to the same class+stream (we are about to
        # regenerate them and they shouldn't block availability checks)
        query = query.filter(~((TimeTableSlot.class_id == exclude_class_id) & (TimeTableSlot.stream_id == exclude_stream_id)))

    # Overlap condition: existing.start_time < end_time AND existing.end_time > start_time
    conflict = query.filter(
        TimeTableSlot.start_time < end_time,
        TimeTableSlot.end_time > start_time
    ).first()

    return conflict is not None

admin_routes = Blueprint("admin_routes", __name__)

# In-memory store for backup job progress. Keyed by job_id.
BACKUP_PROGRESS = {}

def get_redis_client():
    """Return a redis client or None if redis is not configured/installed."""
    if redis is None:
        return None
    url = os.getenv('REDIS_URL') or os.getenv('REDIS', 'redis://localhost:6379/0')
    try:
        return redis.Redis.from_url(url)
    except Exception:
        try:
            return redis.Redis(host='localhost', port=6379, db=0)
        except Exception:
            return None

# Utility function to convert 24-hour time to 12-hour AM/PM format
def convert_to_12hour(time_24h):
    """Convert '14:30' to '2:30 PM'"""
    try:
        dt = datetime.strptime(time_24h, '%H:%M')
        return dt.strftime('%I:%M %p')
    except:
        return time_24h

@admin_routes.route("/admin/dashboard")
def dashboard():
    return render_template("admin/dashboard.html")


@admin_routes.route("/admin/system-settings")
def system_settings():
    """Render the System Settings placeholder page. Sidebar buttons are currently placeholders and not linked."""
    return render_template("admin/system_settings.html")

@admin_routes.route("/admin/manage-users")
def manage_users():
    users = User.query.order_by(User.id.asc()).all()
    return render_template("admin/manage_users.html", users=users)

@admin_routes.route("/admin/create-user", methods=["GET", "POST"])
def create_user():
    # ✅ Show all roles except Admin (to prevent creating another Admin via UI)
    roles = Role.query.filter(Role.role_name != "Admin").order_by(Role.role_name.asc()).all()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        role_name = request.form.get("role")

        # ✅ Always resolve role_id from roles table
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            flash("Invalid role selected.", "danger")
            return render_template("admin/create_user.html", roles=roles)

        # ✅ Unique email check
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already exists. Please use a different email.", "danger")
            return render_template("admin/create_user.html", roles=roles,
                                   first_name=first_name, last_name=last_name, email=email)

        # ✅ Hash password
        hashed_password = generate_password_hash(password)

        # ✅ Create user with correct role_id
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            role_id=role.id   # ✅ Always correct mapping
        )
        db.session.add(new_user)
        db.session.commit()

        flash("User created successfully!", "success")
        return redirect(url_for("admin_routes.manage_users"))

    return render_template("admin/create_user.html", roles=roles)

@admin_routes.route("/admin/edit-user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.filter(Role.role_name != "Admin").order_by(Role.role_name.asc()).all()

    if request.method == "POST":
        user.first_name = request.form.get("first_name")
        user.last_name = request.form.get("last_name")
        new_email = request.form.get("email")
        role_name = request.form.get("role")
        password = request.form.get("password")

        # ✅ Always resolve role_id from roles table
        role = Role.query.filter_by(role_name=role_name).first()
        if not role:
            flash("Invalid role selected.", "danger")
            return render_template("admin/edit_user.html", user=user, roles=roles)

        # ✅ Unique email check (exclude current user)
        existing_user = User.query.filter(User.email == new_email, User.id != user.id).first()
        if existing_user:
            flash("Email already exists. Please use a different email.", "danger")
            return render_template("admin/edit_user.html", user=user, roles=roles)

        user.email = new_email
        user.role_id = role.id   # ✅ Always correct mapping

        # ✅ Handle password change
        if user.role.role_name == "Admin":
            if password:
                flash("Admin password cannot be changed.", "warning")
        else:
            if password:
                user.password = generate_password_hash(password)
            db.session.commit()
            flash("User updated successfully!", "success")

        # ✅ Commit changes for non-password fields
        if user.role.role_name == "Admin" or not password:
            db.session.commit()

        return redirect(url_for("admin_routes.manage_users"))

    return render_template("admin/edit_user.html", user=user, roles=roles)

@admin_routes.route("/admin/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "success")
    return redirect(url_for("admin_routes.manage_users"))

# ✅ New Route: Assign Classes & Streams to Teachers
@admin_routes.route("/admin/assign-teacher", methods=["GET", "POST"])
def assign_teacher():
    # Query teachers (users whose role is Teacher)
    teacher_role = Role.query.filter(Role.role_name.ilike('teacher')).first()
    teachers = []
    if teacher_role:
        # fetch all users whose role name is teacher (case-insensitive)
        teachers = User.query.join(Role).filter(Role.role_name.ilike('teacher')).order_by(User.first_name.asc(), User.last_name.asc()).all()

    # Query classes and streams
    classes = Class.query.order_by(Class.name.asc()).all()
    streams = Stream.query.order_by(Stream.name.asc()).all()

    if request.method == "POST":
        teacher_id = request.form.get("teacher_id")
        class_id = request.form.get("class_id")
        stream_id = request.form.get("stream_id")

        # ✅ Save assignment into teacher_assignments table
        assignment = TeacherAssignment(
            teacher_id=teacher_id,
            class_id=class_id,
            stream_id=stream_id
        )
        db.session.add(assignment)
        db.session.commit()

        flash("Teacher assignment saved successfully!", "success")
        return redirect(url_for("admin_routes.assign_teacher"))

    # ✅ Fetch all assignments for the right-side table
    assignments = TeacherAssignment.query.all()

    return render_template("admin/assign_teacher.html",
                           teachers=teachers,
                           classes=classes,
                           streams=streams,
                           assignments=assignments)

# ✅ New Route: Drop Assignment
@admin_routes.route("/admin/drop-assignment/<int:assignment_id>", methods=["POST"])
def drop_assignment(assignment_id):
    assignment = TeacherAssignment.query.get_or_404(assignment_id)
    db.session.delete(assignment)
    db.session.commit()
    flash("Assignment dropped successfully!", "success")
    return redirect(url_for("admin_routes.assign_teacher"))


# ✅ NEW TIMETABLE MANAGEMENT ROUTES

@admin_routes.route("/admin/manage-timetables")
def manage_timetables():
    """Display timetable management interface grouped by class and stream"""
    classes = Class.query.order_by(Class.name.asc()).all()
    streams = Stream.query.order_by(Stream.name.asc()).all()
    subjects = Subject.query.order_by(Subject.name.asc()).all()

    # Get all teacher assignments (teachers assigned to classes)
    teacher_role = Role.query.filter(Role.role_name.ilike('teacher')).first()
    teachers = []
    if teacher_role:
        # fetch all users whose role name is teacher (case-insensitive)
        teachers = User.query.join(Role).filter(Role.role_name.ilike('teacher')).order_by(User.first_name.asc(), User.last_name.asc()).all()

    return render_template("admin/manage_timetables.html",
                         classes=classes,
                         streams=streams,
                         subjects=subjects,
                         teachers=teachers)


@admin_routes.route('/admin/teachers')
def list_teachers():
    """Return all users who have a Role named 'teacher' (case-insensitive). No additional filtering applied."""
    teachers = User.query.join(Role).filter(Role.role_name.ilike('teacher')).order_by(User.first_name.asc(), User.last_name.asc()).all()
    data = []
    for t in teachers:
        data.append({
            'id': t.id,
            'first_name': t.first_name,
            'last_name': t.last_name,
            'email': t.email,
            'role_name': t.role.role_name if t.role else None
        })
    return jsonify({'teachers': data}), 200


@admin_routes.route('/admin/teachers/count')
def count_teachers():
    """Return total number of teachers found by role join (case-insensitive)."""
    total = User.query.join(Role).filter(Role.role_name.ilike('teacher')).count()
    return jsonify({'teacher_count': total}), 200


@admin_routes.route('/admin/teachers/names')
def list_teacher_names():
    """Return only first and last names of all teachers (no email or other fields)."""
    teachers = User.query.join(Role).filter(Role.role_name.ilike('teacher')).order_by(User.first_name.asc(), User.last_name.asc()).all()
    data = []
    for t in teachers:
        data.append({
            'id': t.id,
            'first_name': t.first_name,
            'last_name': t.last_name
        })
    return jsonify({'teacher_names': data}), 200


@admin_routes.route("/admin/timetable/get/<int:class_id>/<int:stream_id>")
def get_timetable(class_id, stream_id):
    """Retrieve timetable slots for a specific class and stream"""
    slots = TimeTableSlot.query.filter_by(class_id=class_id, stream_id=stream_id)\
        .order_by(TimeTableSlot.day_of_week, TimeTableSlot.start_time).all()

    slot_data = []
    for slot in slots:
        slot_data.append({
            'id': slot.id,
            'teacher_id': slot.teacher_id,
            'teacher_name': f"{slot.teacher.first_name} {slot.teacher.last_name}" if slot.teacher else "Unassigned",
            'subject_id': slot.subject_id,
            'subject_name': slot.subject.name if slot.subject else "Unassigned",
            # include classroom if present (some deployments may have this column)
            'classroom': getattr(slot, 'classroom', '') or '',
            'day_of_week': slot.day_of_week,
            'start_time': slot.start_time,
            'end_time': slot.end_time,
        })

    return jsonify({'slots': slot_data})


@admin_routes.route("/admin/timetable/assigned-teachers/<int:class_id>/<int:stream_id>")
def get_assigned_teachers(class_id, stream_id):
    """Get teachers assigned to a specific class and stream"""
    assignments = TeacherAssignment.query.filter_by(
        class_id=class_id,
        stream_id=stream_id
    ).all()

    teachers_data = []
    for assignment in assignments:
        teachers_data.append({
            'id': assignment.teacher_id,
            'name': f"{assignment.teacher.first_name} {assignment.teacher.last_name}",
            'email': assignment.teacher.email
        })

    return jsonify({'assigned_teachers': teachers_data})


@admin_routes.route("/admin/timetable/generate/<int:class_id>/<int:stream_id>", methods=["POST"])
def generate_timetable(class_id, stream_id):
    """Auto-generate timetable for a stream with 40-minute lesson slots.
    Gets ALL teachers with role Teacher and distributes them across all streams.
    Includes the assigned class teacher in each stream's timetable.
    Each teacher teaches different subjects in different streams.
    Includes 20-minute break at 10:00 AM and 40-minute lunch at 1:00 PM."""

    # delegate to shared helper
    success, payload = _generate_timetable_core(class_id, stream_id)
    if not success:
        return jsonify({'error': payload}), 400
    return jsonify(payload), 201


@admin_routes.route("/admin/timetable/generate-all", methods=["POST"])
def generate_all_timetables():
    """Generate timetables for all classes and streams. Returns a summary per stream."""
    classes = Class.query.all()
    streams = Stream.query.all()
    results = []

    for class_obj in classes:
        for stream in streams:
            success, payload = _generate_timetable_core(class_obj.id, stream.id)
            results.append({
                'class_id': class_obj.id,
                'class_name': class_obj.name,
                'stream_id': stream.id,
                'stream_name': stream.name,
                'success': success,
                'payload': payload
            })

    return jsonify({'results': results}), 200


@admin_routes.route("/admin/timetable/counts")
def timetable_counts():
    """Return counts of timetable slots grouped by class and stream."""
    rows = db.session.query(TimeTableSlot.class_id, TimeTableSlot.stream_id, func.count().label('slots'))\
        .group_by(TimeTableSlot.class_id, TimeTableSlot.stream_id)\
        .order_by(TimeTableSlot.class_id, TimeTableSlot.stream_id).all()

    data = []
    for r in rows:
        # resolve names
        cls = Class.query.get(r[0])
        strm = Stream.query.get(r[1])
        data.append({
            'class_id': r[0],
            'class_name': cls.name if cls else None,
            'stream_id': r[1],
            'stream_name': strm.name if strm else None,
            'slots': int(r[2])
        })

    return jsonify({'counts': data}), 200


def _generate_timetable_core(class_id, stream_id):
    """Core routine to generate timetable for a single class_id and stream_id.
    Returns (True, dict) on success or (False, error_message) on failure.
    """
    # Get the assigned class teacher (must be included)
    class_teacher_assignment = TeacherAssignment.query.filter_by(
        class_id=class_id,
        stream_id=stream_id
    ).first()

    if not class_teacher_assignment:
        return False, 'No class teacher assigned to this class/stream'

    # Get ALL teachers with role "Teacher" (case-insensitive), excluding auto-created placeholders
    teacher_role = Role.query.filter(Role.role_name.ilike('teacher')).first()
    if not teacher_role:
        return False, 'Teacher role not found in database'

    # Get ALL teachers (use the entire teachers table; do not limit to those
    # assigned to this class/stream). This ensures the generator can distribute
    # work across the whole teacher pool.
    all_teachers = User.query.join(Role).filter(
        Role.role_name.ilike('teacher')
    ).order_by(User.first_name.asc(), User.last_name.asc()).all()
    if not all_teachers:
        return False, 'No real teachers found (only auto-created placeholders exist)'

    # Ensure class teacher is included in the list
    all_teacher_ids = [t.id for t in all_teachers]
    if class_teacher_assignment.teacher_id not in all_teacher_ids:
        all_teachers.insert(0, class_teacher_assignment.teacher)

    # NOTE: do not delete existing slots here. We'll generate the new set in-memory
    # and only remove & replace the old slots as an atomic persistence step after
    # successful generation. This prevents leaving an empty timetable if generation
    # fails part-way through.

    # Get all subjects
    subjects = Subject.query.all()
    if not subjects:
        return False, 'No subjects available in the database'

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # Generate 40-minute time slots from 8:00 AM to 5:00 PM with breaks
    times = []
    current_time = datetime.strptime('08:00', '%H:%M')
    end_time = datetime.strptime('17:00', '%H:%M')  # 5:00 PM

    while current_time < end_time:
        time_str = current_time.strftime('%H:%M')

        # Skip 20-minute break at 10:00 AM
        if time_str == '10:00':
            current_time += timedelta(minutes=20)  # Skip break duration
        # Skip 40-minute lunch at 1:00 PM (13:00)
        elif time_str == '13:00':
            current_time += timedelta(minutes=40)  # Skip lunch duration
        else:
            # Calculate remaining time until 5:00 PM
            remaining_minutes = (end_time - current_time).total_seconds() / 60

            # If remaining time <= 40 min, use all remaining time; otherwise use 40 min
            lesson_duration = int(remaining_minutes) if remaining_minutes <= 40 else 40

            if lesson_duration > 0:
                times.append({
                    'start': time_str,
                    'duration': lesson_duration
                })
                current_time += timedelta(minutes=lesson_duration)
            else:
                break

    slots_created = 0
    subject_idx = 0
    teacher_idx = 0

    slots_to_save = []

    # For each time slot, assign one teacher teaching one subject
    # Rotate through all teachers and subjects
    for day in days:
        for time_obj in times:
            time_str = time_obj['start']
            duration = time_obj['duration']

            # Get next teacher (round-robin distribution from ALL available teachers)
            # Attempt to find a teacher who is NOT already booked at this time (across any stream).
            teacher = None
            attempts = 0
            start_idx = teacher_idx % len(all_teachers)
            idx = start_idx
            while attempts < len(all_teachers):
                candidate = all_teachers[idx]
                # check for overlap for this candidate teacher
                # When checking availability for generation we should ignore any
                # existing slots that belong to the same class+stream since those
                # are the ones we're about to replace.
                if not teacher_has_overlap(candidate.id, day, time_str, (datetime.strptime(time_str, '%H:%M') + timedelta(minutes=duration)).strftime('%H:%M'),
                                            exclude_class_id=class_id, exclude_stream_id=stream_id):
                    teacher = candidate
                    # set teacher_idx so next iteration continues after this one
                    teacher_idx = idx + 1
                    break
                # move to next candidate
                attempts += 1
                idx = (idx + 1) % len(all_teachers)

            if teacher is None:
                # No available teacher found for this slot/time - fail with a clear message
                return False, f'No available teacher found for {day} at {time_str} (all teachers are already booked)'

            # Get subject (cycle through available subjects)
            subject = subjects[subject_idx % len(subjects)]

            # Calculate end time
            start_dt = datetime.strptime(time_str, '%H:%M')
            end_dt = start_dt + timedelta(minutes=duration)
            end_time_str = end_dt.strftime('%H:%M')

            # Create slot (collect)
            new_slot = TimeTableSlot(
                teacher_id=teacher.id,
                class_id=class_id,
                stream_id=stream_id,
                subject_id=subject.id,
                day_of_week=day,
                start_time=time_str,
                end_time=end_time_str
            )
            slots_to_save.append(new_slot)
            slots_created += 1

            # Rotate to next teacher and subject
            teacher_idx += 1
            subject_idx += 1

    # persist: delete old slots for this class/stream and insert the newly
    # generated slots inside a transaction so we never leave the DB in an
    # empty state if something goes wrong.
    try:
        if slots_to_save:
            # Ensure any prior transaction state is cleared
            try:
                db.session.rollback()
            except Exception:
                # ignore rollback errors; we'll proceed to do the replace
                pass

            # Remove existing slots and insert new ones, then commit.
            # Use explicit commit/rollback to avoid nested-transaction errors
            TimeTableSlot.query.filter_by(
                class_id=class_id,
                stream_id=stream_id
            ).delete(synchronize_session=False)
            db.session.bulk_save_objects(slots_to_save)
            db.session.commit()
        else:
            # Nothing to save (shouldn't happen) -- treat as failure
            return False, 'No slots generated'
    except Exception as e:
        # Ensure session is rolled back so subsequent calls can proceed
        try:
            db.session.rollback()
        except Exception:
            pass
        return False, f'Database error while saving slots: {str(e)}'

    return True, {
        'message': f'✓ Timetable generated! {slots_created} lessons scheduled for {len(all_teachers)} teachers!',
        'slots_created': slots_created,
        'total_teachers': len(all_teachers)
    }



@admin_routes.route("/admin/timetable/edit/<int:slot_id>", methods=["PUT"])
def edit_timetable_slot(slot_id):
    """Edit an existing timetable slot - ONLY teacher_id and subject_id can be changed"""
    slot = TimeTableSlot.query.get_or_404(slot_id)
    data = request.json

    teacher_id = data.get('teacher_id')
    subject_id = data.get('subject_id')

    # ✅ Check teacher double-booking across ANY stream for overlapping times (excluding current slot)
    if teacher_has_overlap(teacher_id, slot.day_of_week, slot.start_time, slot.end_time, exclude_slot_id=slot_id):
        return jsonify({'error': f'Teacher is already assigned to another stream at {slot.start_time} on {slot.day_of_week}'}), 409

    try:
        slot.teacher_id = teacher_id
        slot.subject_id = subject_id
        db.session.commit()
        return jsonify({'message': 'Timetable slot updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_routes.route("/admin/backup-maintenance", methods=["GET", "POST"])
def backup_maintenance():
    """Handle backup and maintenance settings management."""
    try:
        settings = SystemSettings.get_settings()
    except Exception as e:
        db.session.rollback()
        print(f"[BACKUP_MAINTENANCE] Error fetching settings: {str(e)}")
        settings = SystemSettings()  # Return empty settings object

    if request.method == "POST":
        try:
            settings.backup_schedule = request.form.get("backup_schedule", "weekly")
            settings.maintenance_mode = request.form.get("maintenance_mode") == "on"
            settings.maintenance_message = request.form.get("maintenance_message", "")
            settings.auto_backup_enabled = request.form.get("auto_backup_enabled") == "on"
            settings.updated_by_user_id = session.get('user_id')

            db.session.commit()
            flash("Backup & Maintenance settings updated successfully!", "success")
            return redirect(url_for("admin_routes.backup_maintenance"))
        except Exception as e:
            db.session.rollback()
            print(f"[BACKUP_MAINTENANCE] Error updating settings: {str(e)}")
            flash(f"Error updating settings: {str(e)}", "danger")
            return redirect(url_for("admin_routes.backup_maintenance"))

    return render_template("admin/backup_maintenance.html", settings=settings)


@admin_routes.route("/admin/backup-maintenance/download-page", methods=["GET"])
def download_backup_page():
    """Download the backup maintenance page as HTML file with proper UTF-8 encoding."""
    from flask import make_response
    settings = SystemSettings.get_settings()

    # Render the template
    html_content = render_template("admin/backup_maintenance.html", settings=settings)

    # Create a response with proper encoding
    response = make_response(html_content)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename="backup_maintenance.html"'

    return response


@admin_routes.route("/admin/backup-maintenance/trigger", methods=["POST"])
def trigger_backup():
    """Trigger a manual database backup by enqueuing a background job and returning a job id.
    The client can poll /admin/backup-maintenance/backup-progress/<job_id> to receive progress updates.
    """
    from utils.backup_utils import create_backup
    from models.system_settings import SystemSettings

    try:
        # Capture initiating user id here (request context) so background thread can attribute changes
        initiating_user_id = session.get('user_id')
        # create a new job id and initialize progress
        job_id = str(uuid.uuid4())
        BACKUP_PROGRESS[job_id] = {
            'percent': 0,
            'status': 'queued',
            'message': 'Queued',
            'result': None,
            'started_at': None,
            'finished_at': None
        }
        print(f"[BACKUP] Enqueued backup job {job_id} by user {initiating_user_id}")

        def run_backup_job(jid):
            try:
                print(f'[BACKUP] Starting backup job {jid}')
                BACKUP_PROGRESS[jid].update({'status': 'running', 'started_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')})

                def progress_cb(percent, msg=None):
                    try:
                        BACKUP_PROGRESS[jid].update({'percent': int(percent), 'message': msg or ''})
                        print(f'[BACKUP] Progress update: {percent}% - {msg}')
                        # persist to redis if available
                        r = get_redis_client()
                        payload = {'percent': int(percent), 'status': BACKUP_PROGRESS[jid].get('status'), 'message': msg}
                        if r:
                            try:
                                r.set(f'backup:job:{jid}', json.dumps({'progress': payload}), ex=3600)
                                r.publish(f'backup:job:{jid}', json.dumps({'progress': payload}))
                            except Exception:
                                pass
                    except Exception as e:
                        print(f'[BACKUP] Error in progress_cb: {e}')
                        pass

                # Call the backup utility with progress callback
                print(f'[BACKUP] Calling create_backup for job {jid}')
                result = create_backup(description="manual", progress_callback=progress_cb)
                print(f'[BACKUP] create_backup returned: {result}')

                # final update - FORCE 100% if successful
                if result and result.get('success'):
                    print(f'[BACKUP] Backup successful, setting to 100%')
                    BACKUP_PROGRESS[jid].update({
                        'percent': 100,
                        'status': 'finished',
                        'result': result,
                        'finished_at': datetime.utcnow().strftime('%d/%m/%Y %I:%M:%S %p'),
                        # keep entry in memory for a short grace period so clients can poll after completion
                        'expires_at': (datetime.utcnow() + timedelta(seconds=120)).strftime('%Y-%m-%d %H:%M:%S'),
                        'message': 'Backup complete'
                    })
                else:
                    print(f'[BACKUP] Backup failed, setting error status')
                    BACKUP_PROGRESS[jid].update({
                        'percent': 0,
                        'status': 'error',
                        'result': result,
                        'finished_at': datetime.utcnow().strftime('%d/%m/%Y %I:%M:%S %p'),
                        'expires_at': (datetime.utcnow() + timedelta(seconds=120)).strftime('%Y-%m-%d %H:%M:%S'),
                        'message': result.get('message', 'Backup failed')
                    })

                # persist final state to redis and publish
                r = get_redis_client()
                try:
                    payload = {'percent': BACKUP_PROGRESS[jid].get('percent'), 'status': BACKUP_PROGRESS[jid].get('status'), 'result': result, 'finished_at': BACKUP_PROGRESS[jid].get('finished_at')}
                    if r:
                        try:
                            r.set(f'backup:job:{jid}', json.dumps({'progress': payload}), ex=3600)
                            r.publish(f'backup:job:{jid}', json.dumps({'progress': payload}))
                        except Exception as e:
                            print(f'[BACKUP] Error persisting to Redis: {e}')
                except Exception as e:
                    print(f'[BACKUP] Error in Redis persist block: {e}')

                # If successful, update system settings (use app context and captured initiating user id)
                if result.get('success'):
                    try:
                        print(f'[BACKUP] Updating SystemSettings for job {jid}')
                        from flask import current_app
                        with current_app.app_context():
                            settings = SystemSettings.get_settings()
                            settings.last_backup_time = result.get('timestamp')
                            # use the captured initiating user id rather than session in background thread
                            settings.updated_by_user_id = initiating_user_id
                            db.session.add(settings)
                            db.session.commit()
                        print(f'[BACKUP] SystemSettings updated successfully for job {jid}')
                    except Exception as e:
                        print(f'[BACKUP] Error updating SystemSettings for job {jid}: {e}')
                        try:
                            from flask import current_app
                            with current_app.app_context():
                                db.session.rollback()
                        except Exception:
                            pass
                        print(f'[BACKUP] Rolled back SystemSettings update')

            except Exception as e:
                print(f'[BACKUP] Exception in run_backup_job {jid}: {e}')
                import traceback
                traceback.print_exc()
                try:
                    BACKUP_PROGRESS[jid].update({'status': 'error', 'message': str(e), 'finished_at': datetime.utcnow().strftime('%d/%m/%Y %I:%M:%S %p')})
                except Exception:
                    pass

        # start the background thread
        t = threading.Thread(target=run_backup_job, args=(job_id,), daemon=True)
        t.start()

        # Return job id for client to poll
        return jsonify({'success': True, 'job_id': job_id}), 202

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Backup enqueue error: {str(e)}'}), 500


@admin_routes.route("/admin/backup-maintenance/list", methods=["GET"])
def list_backups():
    """Get list of all available backups as JSON."""
    from utils.backup_utils import list_backups as get_backups

    try:
        backups = get_backups()
        return jsonify({
            'success': True,
            'backups': [
                {
                    'filename': b['filename'],
                    'size_mb': b['size_mb'],
                    'created': b['created'].strftime('%Y-%m-%d %H:%M:%S')
                }
                for b in backups
            ]
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error listing backups: {str(e)}'
        }), 500


@admin_routes.route("/admin/backup-maintenance/backup-progress/<job_id>", methods=["GET"])
def backup_progress(job_id):
    """Return progress for a given backup job id (in-memory store)."""
    try:
        print(f"[BACKUP] Progress GET requested for job {job_id}")
        data = BACKUP_PROGRESS.get(job_id)
        if not data:
            print(f"[BACKUP] Job {job_id} not found in BACKUP_PROGRESS")
            return jsonify({'success': False, 'message': 'Job not found'}), 404

        # If entry has an expires_at timestamp, and it's past expiry, remove it and return 404
        expires_at = data.get('expires_at')
        if expires_at:
            try:
                expires_dt = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                if datetime.utcnow() > expires_dt:
                    print(f"[BACKUP] Job {job_id} expired at {expires_at}, removing from memory")
                    try:
                        del BACKUP_PROGRESS[job_id]
                    except Exception:
                        pass
                    return jsonify({'success': False, 'message': 'Job not found'}), 404
            except Exception:
                # if parsing fails, continue to return the entry
                pass

        print(f"[BACKUP] Returning progress for job {job_id}: {data.get('percent')}% status={data.get('status')}")
        return jsonify({'success': True, 'progress': data}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error retrieving progress: {str(e)}'}), 500


@admin_routes.route('/admin/backup-maintenance/backup-progress-sse/<job_id>')
def backup_progress_sse(job_id):
    """SSE endpoint that streams progress updates for the given job_id.
    Uses in-memory state with polling to ensure client always gets final 100% update.
    """
    import time

    def gen():
        sent_count = 0
        last_snapshot = None
        timeout = time.time() + 300  # 5 minute timeout
        print(f'[SSE] New SSE generator started for job {job_id}')

        try:
            while time.time() < timeout:
                try:
                    state = BACKUP_PROGRESS.get(job_id)

                    # Only send if state changed (compare JSON snapshot to handle in-place dict mutation)
                    if state:
                        try:
                                snapshot = json.dumps(state, sort_keys=True, default=str)
                        except Exception:
                            snapshot = str(state)

                            if snapshot != last_snapshot:
                                # ensure we can serialize datetime objects, use default=str
                                payload = json.dumps({'progress': state}, default=str)
                            yield f'data: {payload}\n\n'
                            sent_count += 1
                            print(f'[SSE] Sent update for job {job_id}: {state.get("percent")}% - {state.get("status")}')
                            last_snapshot = snapshot

                            # If finished, send one more time then stop
                            if state.get('status') == 'finished' or (state.get('percent') and state.get('percent') >= 100):
                                # send final confirmation
                                try:
                                    final_payload = json.dumps({'progress': state}, default=str)
                                    yield f'data: {final_payload}\n\n'
                                    sent_count += 1
                                except Exception:
                                    pass
                                print(f'[SSE] Job {job_id} finished, closing connection after {sent_count} messages')
                                break

                    # Poll every 100ms while job is running
                    time.sleep(0.1)

                except Exception as e:
                    print(f'[SSE] Error in polling loop for {job_id}: {e}')
                    time.sleep(0.5)

        except GeneratorExit:
            print(f'[SSE] Client closed connection for job {job_id} after {sent_count} messages')
            return
        except Exception as e:
            print(f'[SSE] Generator error for job {job_id}: {e}')
            return

    response = current_app.response_class(gen(), mimetype='text/event-stream')
    # ✅ Add required SSE headers
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'  # Disable proxy buffering
    return response


@admin_routes.route("/admin/backup-maintenance/download/<filename>", methods=["GET"])
def download_backup(filename):
    """Download a specific backup file."""
    from utils.backup_utils import BACKUP_DIR
    from flask import send_file
    import os

    try:
        # Validate filename to prevent directory traversal attacks
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400

        backup_path = os.path.join(BACKUP_DIR, filename)

        # Verify file exists
        if not os.path.exists(backup_path):
            return jsonify({'error': 'Backup file not found'}), 404

        # Verify it's actually a backup file (ends with .gz)
        if not filename.endswith('.gz'):
            return jsonify({'error': 'Invalid file type'}), 400

        # Use Flask's send_file with binary mimetype to prevent browser decompression
        # application/octet-stream tells browser "this is binary data, don't try to decompress"
        return send_file(
            backup_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 500


@admin_routes.route("/admin/backup-maintenance/delete/<filename>", methods=["POST"])
def delete_backup(filename):
    """Delete a specific backup file and return JSON status."""
    from utils.backup_utils import delete_backup as delete_backup_util

    try:
        # Basic validation to prevent directory traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'message': 'Invalid filename'}), 400

        print(f"[DELETE_BACKUP] Attempting to delete: {filename}")
        result = delete_backup_util(filename)
        print(f"[DELETE_BACKUP] Result: {result}")

        if result.get('success'):
            # Update system settings last_backup_time to latest remaining backup (or None)
            try:
                from utils.backup_utils import get_latest_backup
                latest = get_latest_backup()
                settings = SystemSettings.get_settings()
                if latest:
                    settings.last_backup_time = latest.get('created')
                else:
                    settings.last_backup_time = None
                settings.updated_by_user_id = session.get('user_id')
                db.session.commit()
            except Exception as e:
                # If updating settings fails, log to console but still return success for delete
                print(f"Warning: failed to update SystemSettings after deleting backup: {e}")

            return jsonify({'success': True, 'message': result.get('message', 'Backup deleted')}), 200
        else:
            return jsonify({'success': False, 'message': result.get('message', 'Unable to delete backup')}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Delete error: {str(e)}'}), 500


@admin_routes.route("/admin/api/backup-settings", methods=["GET"])
def get_backup_settings():
    """API endpoint to get current backup settings (used by frontend to refresh after backup completes)."""
    try:
        settings = SystemSettings.get_settings()
        # Format timestamp in East African format: DD/MM/YYYY HH:MM:SS AM/PM
        if settings.last_backup_time:
            time_str = settings.last_backup_time.strftime('%d/%m/%Y %I:%M:%S %p')
        else:
            time_str = None

        return jsonify({
            'success': True,
            'last_backup_time': time_str,
            'auto_backup_enabled': settings.auto_backup_enabled,
            'backup_schedule': settings.backup_schedule,
            'maintenance_mode': settings.maintenance_mode
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@admin_routes.route('/admin/debug/backup-progresses', methods=['GET'])
def debug_backup_progresses():
    """Debug route to list current in-memory backup progress entries. For development only."""
    try:
        keys = list(BACKUP_PROGRESS.keys())
        summary = {k: {'percent': BACKUP_PROGRESS[k].get('percent'), 'status': BACKUP_PROGRESS[k].get('status')} for k in keys}
        print(f"[DEBUG] Current BACKUP_PROGRESS keys: {keys}")
        return jsonify({'success': True, 'count': len(keys), 'summary': summary}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500