from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.user_models import db, User, Role
from models.class_model import Class
from models.stream_model import Stream
from models.marks_model import Subject
from models.teacher_assignment_models import TeacherAssignment
from models.timetable_model import TimeTableSlot
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

admin_routes = Blueprint("admin_routes", __name__)

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
    teacher_role = Role.query.filter_by(role_name="Teacher").first()
    teachers = []
    if teacher_role:
        teachers = User.query.filter_by(role_id=teacher_role.id).order_by(User.first_name.asc()).all()

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
    teacher_role = Role.query.filter_by(role_name="Teacher").first()
    teachers = []
    if teacher_role:
        teachers = User.query.filter_by(role_id=teacher_role.id).order_by(User.first_name.asc()).all()

    return render_template("admin/manage_timetables.html",
                         classes=classes,
                         streams=streams,
                         subjects=subjects,
                         teachers=teachers)


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

    # Get the assigned class teacher (must be included)
    class_teacher_assignment = TeacherAssignment.query.filter_by(
        class_id=class_id,
        stream_id=stream_id
    ).first()

    if not class_teacher_assignment:
        return jsonify({'error': 'No class teacher assigned to this class/stream'}), 400

    # Get ALL teachers with role "Teacher"
    teacher_role = Role.query.filter_by(role_name="Teacher").first()
    if not teacher_role:
        return jsonify({'error': 'Teacher role not found in database'}), 400

    all_teachers = User.query.filter_by(role_id=teacher_role.id).all()
    if not all_teachers:
        return jsonify({'error': 'No teachers available in the system'}), 400

    # Ensure class teacher is included in the list
    all_teacher_ids = [t.id for t in all_teachers]
    if class_teacher_assignment.teacher_id not in all_teacher_ids:
        all_teachers.insert(0, class_teacher_assignment.teacher)

    # Clear existing slots for this class/stream
    TimeTableSlot.query.filter_by(
        class_id=class_id,
        stream_id=stream_id
    ).delete()

    # Get all subjects
    subjects = Subject.query.all()
    if not subjects:
        return jsonify({'error': 'No subjects available in the database'}), 400

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    # Generate 40-minute time slots from 8:00 AM to 5:00 PM with breaks
    times = []
    from datetime import datetime, timedelta
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

    # For each time slot, assign one teacher teaching one subject
    # Rotate through all teachers and subjects
    for day in days:
        for time_obj in times:
            time_str = time_obj['start']
            duration = time_obj['duration']

            # Get next teacher (round-robin distribution from ALL available teachers)
            teacher = all_teachers[teacher_idx % len(all_teachers)]

            # Get subject (cycle through available subjects)
            subject = subjects[subject_idx % len(subjects)]

            # Calculate end time
            start_dt = datetime.strptime(time_str, '%H:%M')
            end_dt = start_dt + timedelta(minutes=duration)
            end_time_str = end_dt.strftime('%H:%M')

            # Create slot
            new_slot = TimeTableSlot(
                teacher_id=teacher.id,
                class_id=class_id,
                stream_id=stream_id,
                subject_id=subject.id,
                day_of_week=day,
                start_time=time_str,
                end_time=end_time_str
            )
            db.session.add(new_slot)
            slots_created += 1

            # Rotate to next teacher and subject
            teacher_idx += 1
            subject_idx += 1

    db.session.commit()
    return jsonify({
        'message': f'✓ Timetable generated! {slots_created} lessons scheduled for {len(all_teachers)} teachers!',
        'slots_created': slots_created,
        'total_teachers': len(all_teachers)
    }), 201



@admin_routes.route("/admin/timetable/edit/<int:slot_id>", methods=["PUT"])
def edit_timetable_slot(slot_id):
    """Edit an existing timetable slot - ONLY teacher_id and subject_id can be changed"""
    slot = TimeTableSlot.query.get_or_404(slot_id)
    data = request.json

    teacher_id = data.get('teacher_id')
    subject_id = data.get('subject_id')

    # ✅ Check teacher double-booking for SAME STREAM at SAME TIME (excluding current slot)
    teacher_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.id != slot_id,
        TimeTableSlot.teacher_id == teacher_id,
        TimeTableSlot.stream_id == slot.stream_id,
        TimeTableSlot.day_of_week == slot.day_of_week,
        TimeTableSlot.start_time == slot.start_time
    ).first()

    if teacher_conflict:
        return jsonify({'error': f'Teacher is already assigned to this stream at {slot.start_time} on {slot.day_of_week}'}), 409

    try:
        slot.teacher_id = teacher_id
        slot.subject_id = subject_id
        db.session.commit()
        return jsonify({'message': 'Timetable slot updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500