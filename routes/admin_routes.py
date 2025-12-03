from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.user_models import db, User, Role
from models.class_model import Class
from models.stream_model import Stream
from models.marks_model import Subject
from models.teacher_assignment_models import TeacherAssignment
from models.timetable_model import TimeTableSlot
from werkzeug.security import generate_password_hash

admin_routes = Blueprint("admin_routes", __name__)

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
    """Auto-generate timetable for assigned teachers with proper distribution.
    Each class/stream has 3 teachers, each teaching different subjects at different times."""

    # Get all assigned teachers for this class/stream (should be 3)
    assignments = TeacherAssignment.query.filter_by(
        class_id=class_id,
        stream_id=stream_id
    ).all()

    if not assignments:
        return jsonify({'error': 'No teachers assigned to this class/stream'}), 400

    if len(assignments) < 3:
        return jsonify({
            'error': f'This class/stream should have 3 teachers. Currently has {len(assignments)}. Please assign all 3 teachers first.'
        }), 400

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
    times = ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00']

    slots_created = 0
    subject_idx = 0

    # For each time slot, assign all 3 teachers (rotating through subjects)
    from datetime import datetime, timedelta
    for day in days:
        for time in times:
            # Each time slot gets all 3 teachers teaching different subjects
            for teacher_idx, assignment in enumerate(assignments):
                # Get subject for this teacher (cycle through available subjects)
                current_subject_idx = (subject_idx + teacher_idx) % len(subjects)
                subject = subjects[current_subject_idx]

                # Calculate end time (1 hour after start)
                start_dt = datetime.strptime(time, '%H:%M')
                end_dt = start_dt + timedelta(hours=1)
                end_time = end_dt.strftime('%H:%M')

                # Create slot
                new_slot = TimeTableSlot(
                    teacher_id=assignment.teacher_id,
                    class_id=class_id,
                    stream_id=stream_id,
                    subject_id=subject.id,
                    day_of_week=day,
                    start_time=time,
                    end_time=end_time
                )
                db.session.add(new_slot)
                slots_created += 1

            subject_idx += 1

    db.session.commit()
    return jsonify({
        'message': f'✓ Timetable generated successfully! All 3 teachers assigned across {slots_created} slots!',
        'slots_created': slots_created
    }), 201


@admin_routes.route("/admin/timetable/add", methods=["POST"])
def add_timetable_slot():
    """Add a new timetable slot with conflict validation"""
    data = request.json

    teacher_id = data.get('teacher_id')
    class_id = data.get('class_id')
    stream_id = data.get('stream_id')
    subject_id = data.get('subject_id')
    day_of_week = data.get('day_of_week')
    start_time = data.get('start_time')

    # ✅ Validate required fields
    if not all([teacher_id, class_id, stream_id, subject_id, day_of_week, start_time]):
        return jsonify({'error': 'Missing required fields'}), 400

    # ✅ Calculate end_time (one hour after start_time)
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = start_dt + timedelta(hours=1)
        end_time = end_dt.strftime('%H:%M')
    except ValueError:
        return jsonify({'error': 'Invalid time format'}), 400

    # ✅ Check teacher double-booking (same day, overlapping time)
    teacher_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.teacher_id == teacher_id,
        TimeTableSlot.day_of_week == day_of_week,
        TimeTableSlot.start_time == start_time
    ).first()

    if teacher_conflict:
        return jsonify({'error': f'Teacher is already assigned at {start_time} on {day_of_week}'}), 409

    # ✅ Check class double-booking (same day, overlapping time)
    class_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.class_id == class_id,
        TimeTableSlot.stream_id == stream_id,
        TimeTableSlot.day_of_week == day_of_week,
        TimeTableSlot.start_time == start_time
    ).first()

    if class_conflict:
        return jsonify({'error': f'Class {day_of_week} {start_time} slot is already occupied'}), 409

    # ✅ Create and save new slot
    new_slot = TimeTableSlot(
        teacher_id=teacher_id,
        class_id=class_id,
        stream_id=stream_id,
        subject_id=subject_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time
    )

    try:
        db.session.add(new_slot)
        db.session.commit()
        return jsonify({
            'id': new_slot.id,
            'message': 'Timetable slot added successfully!'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_routes.route("/admin/timetable/delete/<int:slot_id>", methods=["DELETE"])
def delete_timetable_slot(slot_id):
    """Delete a timetable slot"""
    slot = TimeTableSlot.query.get_or_404(slot_id)

    try:
        db.session.delete(slot)
        db.session.commit()
        return jsonify({'message': 'Timetable slot deleted successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_routes.route("/admin/timetable/edit/<int:slot_id>", methods=["PUT"])
def edit_timetable_slot(slot_id):
    """Edit an existing timetable slot"""
    slot = TimeTableSlot.query.get_or_404(slot_id)
    data = request.json

    teacher_id = data.get('teacher_id')
    subject_id = data.get('subject_id')
    day_of_week = data.get('day_of_week')
    start_time = data.get('start_time')

    # ✅ Calculate end_time (one hour after start_time)
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = start_dt + timedelta(hours=1)
        end_time = end_dt.strftime('%H:%M')
    except ValueError:
        return jsonify({'error': 'Invalid time format'}), 400

    # ✅ Check teacher double-booking (excluding current slot)
    teacher_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.id != slot_id,
        TimeTableSlot.teacher_id == teacher_id,
        TimeTableSlot.day_of_week == day_of_week,
        TimeTableSlot.start_time == start_time
    ).first()

    if teacher_conflict:
        return jsonify({'error': f'Teacher is already assigned at {start_time} on {day_of_week}'}), 409

    # ✅ Check class double-booking (excluding current slot)
    class_conflict = TimeTableSlot.query.filter(
        TimeTableSlot.id != slot_id,
        TimeTableSlot.class_id == slot.class_id,
        TimeTableSlot.stream_id == slot.stream_id,
        TimeTableSlot.day_of_week == day_of_week,
        TimeTableSlot.start_time == start_time
    ).first()

    if class_conflict:
        return jsonify({'error': f'Class {day_of_week} {start_time} slot is already occupied'}), 409

    try:
        slot.teacher_id = teacher_id
        slot.subject_id = subject_id
        slot.day_of_week = day_of_week
        slot.start_time = start_time
        slot.end_time = end_time
        db.session.commit()
        return jsonify({'message': 'Timetable slot updated successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500