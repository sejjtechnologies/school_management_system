from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from models.user_models import db, User, Role
from models.term_model import Term
from models.register_pupils import Pupil
from models.timetable_model import TimeTableSlot
from models.attendance_model import Attendance
from models.marks_model import Mark, Subject
from models.register_pupils import Payment
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from sqlalchemy import or_

parent_routes = Blueprint("parent_routes", __name__)

# ✅ Dashboard Route
@parent_routes.route("/parent/dashboard")
def dashboard():
    """Parent dashboard - requires login"""
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to access the parent dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    user = User.query.get(user_id)
    if not user or user.role.role_name.lower() != "parent":
        flash("Access denied. Only parents can view this dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    return render_template("parent/dashboard.html", parent=user)

# ✅ API: Search for Child
@parent_routes.route("/api/parent/search-child", methods=["GET"])
def search_child():
    """Search for child by name, admission number, pupil ID, or roll number"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    search_query = request.args.get("q", "").strip()
    if not search_query or len(search_query) < 2:
        return jsonify({"error": "Search query too short"}), 400

    try:
        # Search for pupils by various fields (first/middle/last name, admission number, pupil id, roll number)
        like_q = f"%{search_query}%"
        pupils = Pupil.query.filter(
            or_(
                Pupil.first_name.ilike(like_q),
                Pupil.middle_name.ilike(like_q),
                Pupil.last_name.ilike(like_q),
                Pupil.admission_number.ilike(like_q),
                Pupil.pupil_id.ilike(like_q),
                Pupil.roll_number.ilike(like_q)
            )
        ).all()

        if not pupils:
            return jsonify({"error": "No pupils found"}), 404

        # Return first 5 results
        results = []
        for pupil in pupils[:5]:
            parts = [pupil.first_name or "", pupil.middle_name or "", pupil.last_name or ""]
            full_name = " ".join([p.strip() for p in parts if p and p.strip()])

            class_name = None
            stream_name = None
            try:
                if hasattr(pupil, 'class_') and pupil.class_:
                    class_name = getattr(pupil.class_, 'name', None)
            except Exception:
                class_name = None
            try:
                if hasattr(pupil, 'stream') and pupil.stream:
                    stream_name = getattr(pupil.stream, 'name', None)
            except Exception:
                stream_name = None

            results.append({
                "id": pupil.id,
                "name": full_name,
                "admission_number": pupil.admission_number,
                "pupil_id": pupil.pupil_id,
                "roll_number": pupil.roll_number,
                "class_id": pupil.class_id,
                "class_name": class_name,
                "stream_id": pupil.stream_id,
                "stream_name": stream_name,
                "status": getattr(pupil, 'enrollment_status', None) or getattr(pupil, 'status', None) or 'Active'
            })

        try:
            user = User.query.get(user_id)
            if user and user.role and user.role.role_name.lower() == 'parent' and len(results) > 0:
                session['parent_selected_pupil_id'] = results[0]['id']
        except Exception:
            pass

        return jsonify({"pupils": results}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


    # API: Attendance summary (JSON) - includes teacher-recorded breakdown
@parent_routes.route("/api/parent/pupil/<int:pupil_id>/attendance-summary", methods=["GET"])
def attendance_summary(pupil_id):
    """Return JSON summary of attendance for pupil for period=day|week|month|term and reference date=date=YYYY-MM-DD.
    Also returns counts of records recorded by users with role 'Teacher'."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Basic authorization: allow parents to query their pupil (reuse logic from view_attendance)
    pupil = Pupil.query.get_or_404(pupil_id)
    user = User.query.get(user_id)
    if user and user.role and user.role.role_name.lower() == 'parent':
        allowed = False
        try:
            if getattr(pupil, 'email', None) and user.email and pupil.email.lower() == user.email.lower():
                allowed = True
            guardian_name = getattr(pupil, 'guardian_name', '') or ''
            if not allowed and guardian_name:
                if user.first_name.lower() in guardian_name.lower() or user.last_name.lower() in guardian_name.lower():
                    allowed = True
            selected = session.get('parent_selected_pupil_id')
            if not allowed and selected and int(selected) == int(pupil.id):
                allowed = True
        except Exception:
            allowed = False

        if not allowed:
            return jsonify({"error": "Access denied"}), 403

    # Determine period and ref date
    period = request.args.get('period', 'week')
    date_str = request.args.get('date', None)
    from datetime import datetime, date, timedelta

    try:
        if date_str:
            ref_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            ref_date = date.today()
    except Exception:
        ref_date = date.today()

    # compute start_date and end_date
    if period == 'day':
        start_date = end_date = ref_date
    elif period == 'week':
        start_date = ref_date - timedelta(days=ref_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = ref_date.replace(day=1)
        if ref_date.month == 12:
            next_month = ref_date.replace(year=ref_date.year + 1, month=1, day=1)
        else:
            next_month = ref_date.replace(month=ref_date.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
    else:
        # Try to use Term table if available
        term = Term.query.filter(Term.start_date <= ref_date, Term.end_date >= ref_date).first()
        if term:
            start_date = term.start_date
            end_date = term.end_date
        else:
            # fallback to 3.5 months (105 days) ending on ref_date
            end_date = ref_date
            start_date = ref_date - timedelta(days=104)

    # Query attendance in window
    records = Attendance.query.filter(
        Attendance.pupil_id == pupil_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    # Totals
    total = len(records)
    counts = {"present": 0, "absent": 0, "late": 0, "leave": 0}
    for r in records:
        st = (r.status or '').lower()
        if st in counts:
            counts[st] += 1

    # Teacher-recorded breakdown
    # Join Attendance -> User -> Role to find records recorded by users with role 'Teacher'
    teacher_records = Attendance.query.join(User, Attendance.recorded_by == User.id).join(Role).filter(
        Role.role_name.ilike('teacher'),
        Attendance.pupil_id == pupil_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    teacher_total = len(teacher_records)
    teacher_counts = {"present": 0, "absent": 0, "late": 0, "leave": 0}
    for r in teacher_records:
        st = (r.status or '').lower()
        if st in teacher_counts:
            teacher_counts[st] += 1

    # Build optional record list (limited)
    rec_list = [
        {"date": r.date.isoformat(), "status": r.status, "reason": r.reason, "recorded_by": r.recorded_by}
        for r in records[:200]
    ]

    return jsonify({
        "pupil_id": pupil_id,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_records": total,
        "counts": counts,
        "teacher_records_total": teacher_total,
        "teacher_counts": teacher_counts,
        "records_sample": rec_list
    })

# ✅ View Timetable
@parent_routes.route("/parent/pupil/<int:pupil_id>/timetable")
def view_timetable(pupil_id):
    """View pupil's class timetable"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)

    # Authorization: if the logged-in user is a parent, ensure they are a guardian of this pupil.
    # There is no strict FK linking parents to pupils in the current schema, so we attempt
    # a best-effort match: allow access if the parent's email matches the pupil email or
    # the parent's name appears in the guardian_name. If the check fails, deny access.
    user = User.query.get(user_id)
    if user and user.role and user.role.role_name.lower() == 'parent':
        allowed = False
        try:
            # match by pupil.email
            if getattr(pupil, 'email', None) and user.email and pupil.email.lower() == user.email.lower():
                allowed = True
            # match by guardian_name containing parent's name
            guardian_name = getattr(pupil, 'guardian_name', '') or ''
            if not allowed and guardian_name:
                if user.first_name.lower() in guardian_name.lower() or user.last_name.lower() in guardian_name.lower():
                    allowed = True
            # allow if the parent selected this pupil during search in this session
            selected = session.get('parent_selected_pupil_id')
            if not allowed and selected and int(selected) == int(pupil.id):
                allowed = True
        except Exception:
            allowed = False

        if not allowed:
            flash('Access denied. You can only view timetables for your own child. If this is an error, contact the school administrator.', 'danger')
            return redirect(url_for('parent_routes.dashboard'))

    # Get timetable slots for the pupil's class and stream
    timetable = TimeTableSlot.query.filter_by(
        class_id=pupil.class_id,
        stream_id=pupil.stream_id
    ).all()

    # Group by day and time
    schedule = {}
    for slot in timetable:
        # Only include slots that have a teacher and subject assigned (no TBA)
        if not slot.teacher or not slot.subject:
            continue

        day = slot.day_of_week
        if day not in schedule:
            schedule[day] = []

        schedule[day].append({
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "subject": slot.subject.name,
            # `slot.teacher` is a User instance. Get full name (first_name + last_name).
            "teacher": f"{slot.teacher.first_name} {slot.teacher.last_name}".strip(),
            # Include classroom only if present. Use getattr to avoid AttributeError.
            "classroom": getattr(slot, 'classroom', None)
        })

    # Gather class teacher, academic year, and term information
    class_teacher = None
    academic_year = None
    term = None

    try:
        # Query TeacherAssignment table to find the class teacher assigned to this stream
        assignment = TeacherAssignment.query.filter_by(
            class_id=pupil.class_id,
            stream_id=pupil.stream_id
        ).first()
        if assignment and assignment.teacher:
            class_teacher = f"{assignment.teacher.first_name} {assignment.teacher.last_name}".strip()
    except Exception:
        class_teacher = None

    try:
        # Try to retrieve current academic year and term
        # These may be stored in a settings table, environment variable, or config
        # For now, use placeholders; customize as needed
        academic_year = getattr(pupil, 'academic_year', None) or "2025"
        term = getattr(pupil, 'term', None) or "Term 1"
    except Exception:
        academic_year = "2025"
        term = "Term 1"

    return render_template(
        "parent/timetable.html",
        pupil=pupil,
        schedule=schedule,
        class_teacher=class_teacher,
        academic_year=academic_year,
        term=term
    )

# ✅ View Attendance
@parent_routes.route("/parent/pupil/<int:pupil_id>/attendance")
def view_attendance(pupil_id):
    """View pupil's attendance records"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)
    # Determine period filter (day|week|month|term) and reference date
    period = request.args.get('period', 'week')
    date_str = request.args.get('date', None)
    from datetime import datetime, date, timedelta

    try:
        if date_str:
            ref_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            ref_date = date.today()
    except Exception:
        ref_date = date.today()

    # compute start_date and end_date for the selected period
    if period == 'day':
        start_date = end_date = ref_date
    elif period == 'week':
        # Week starting Monday
        start_date = ref_date - timedelta(days=ref_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        # first day of month
        start_date = ref_date.replace(day=1)
        # compute last day of month
        if ref_date.month == 12:
            next_month = ref_date.replace(year=ref_date.year + 1, month=1, day=1)
        else:
            next_month = ref_date.replace(month=ref_date.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
    else:
        # term = approx 3.5 months = 105 days ending on ref_date
        end_date = ref_date
        start_date = ref_date - timedelta(days=104)

    # Query attendance records for the pupil within the window
    attendance_records = Attendance.query.filter(
        Attendance.pupil_id == pupil_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).order_by(Attendance.date.asc()).all()

    # Calculate stats
    total_days = len(attendance_records)
    present_days = len([a for a in attendance_records if a.status and a.status.lower() == "present"])
    absent_days = len([a for a in attendance_records if a.status and a.status.lower() == "absent"])
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    return render_template(
        "parent/attendance.html",
        pupil=pupil,
        attendance_records=attendance_records,
        stats={
            "total": total_days,
            "present": present_days,
            "absent": absent_days,
            "percentage": round(attendance_percentage, 1)
        },
        period=period,
        date=ref_date.isoformat(),
        start_date=start_date,
        end_date=end_date
    )

# ✅ View Academic Reports
@parent_routes.route("/parent/pupil/<int:pupil_id>/reports")
def view_reports(pupil_id):
    """View pupil's academic reports and marks"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)

    # Get marks by subject
    marks = Mark.query.filter_by(pupil_id=pupil_id).all()

    # Group by subject
    subjects_marks = {}
    for mark in marks:
        subject_name = mark.subject.name if mark.subject else "Unknown"
        if subject_name not in subjects_marks:
            subjects_marks[subject_name] = []
        subjects_marks[subject_name].append({
            "score": mark.score,
            "max_score": mark.max_score,
            "percentage": (mark.score / mark.max_score * 100) if mark.max_score > 0 else 0,
            "term": mark.term if hasattr(mark, 'term') else "Current"
        })

    return render_template(
        "parent/reports.html",
        pupil=pupil,
        subjects_marks=subjects_marks
    )

# ✅ View Payment Status
@parent_routes.route("/parent/pupil/<int:pupil_id>/payment-status")
def view_payment_status(pupil_id):
    """View pupil's payment status and outstanding fees"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)

    # Get payment records
    payments = Payment.query.filter_by(pupil_id=pupil_id).all()

    # Calculate summary
    total_fees = sum(p.amount for p in payments if p.status == "pending")
    total_paid = sum(p.amount for p in payments if p.status == "completed")

    return render_template(
        "parent/payment_status.html",
        pupil=pupil,
        payments=payments,
        summary={
            "outstanding": total_fees,
            "paid": total_paid,
            "total": total_fees + total_paid
        }
    )

# ✅ View Account Balance
@parent_routes.route("/parent/pupil/<int:pupil_id>/balance")
def view_balance(pupil_id):
    """View pupil's account balance"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)

    # Calculate balance from payments
    payments = Payment.query.filter_by(pupil_id=pupil_id).all()

    total_owed = sum(p.amount for p in payments if p.status == "pending")
    total_paid = sum(p.amount for p in payments if p.status == "completed")

    balance_status = "Credit" if total_paid > total_owed else "Debit"
    balance_amount = abs(total_paid - total_owed)

    return render_template(
        "parent/balance.html",
        pupil=pupil,
        balance={
            "status": balance_status,
            "amount": balance_amount,
            "outstanding": total_owed,
            "paid": total_paid
        }
    )

# ✅ View Payment Receipts
@parent_routes.route("/parent/pupil/<int:pupil_id>/receipts")
def view_receipts(pupil_id):
    """View pupil's payment receipts"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)

    # Get receipts (using payments table as source for receipts)
    receipts = Payment.query.filter_by(pupil_id=pupil_id).all()

    return render_template(
        "parent/receipts.html",
        pupil=pupil,
        receipts=receipts
    )

# ✅ Download Receipt (if applicable)
@parent_routes.route("/parent/receipt/<int:receipt_id>/download")
def download_receipt(receipt_id):
    """Download payment receipt as PDF"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    # Placeholder: receipts are stored in payments table; adjust when receipts model exists
    receipt = Payment.query.get_or_404(receipt_id)

    # TODO: Implement PDF generation and download
    flash("Receipt download functionality coming soon.", "info")
    return redirect(request.referrer or url_for("parent_routes.dashboard"))