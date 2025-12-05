from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from models.user_models import db, User
from models.register_pupils import Pupil
from models.timetable_model import TimeTableSlot
from models.attendance_model import Attendance
from models.marks_model import Mark, Subject
from models.register_pupils import Payment
from models.class_model import Class
from models.stream_model import Stream
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
            # Build a display name from available name parts
            parts = [pupil.first_name or "", pupil.middle_name or "", pupil.last_name or ""]
            full_name = " ".join([p.strip() for p in parts if p and p.strip()])

            # Resolve class and stream names if relationships exist
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

        # If the searching user is a parent, remember the first result in session so
        # subsequent detail requests (timetable, attendance) can be authorized.
        try:
            user = User.query.get(user_id)
            if user and user.role and user.role.role_name.lower() == 'parent' and len(results) > 0:
                # store the first result as the selected pupil for this session
                session['parent_selected_pupil_id'] = results[0]['id']
        except Exception:
            # non-fatal; don't block returning results
            pass

        return jsonify({"pupils": results}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        day = slot.day_of_week
        if day not in schedule:
            schedule[day] = []
        schedule[day].append({
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "subject": slot.subject.name if slot.subject else "TBA",
            # `slot.teacher` is a User instance. Get full name (first_name + last_name).
            "teacher": (f"{slot.teacher.first_name} {slot.teacher.last_name}".strip() if slot.teacher else "TBA"),
            # Some deployments may not have a `classroom` column on TimeTableSlot.
            # Use getattr to avoid AttributeError and fall back to "TBA".
            "classroom": getattr(slot, 'classroom', None) or "TBA"
        })

    return render_template(
        "parent/timetable.html",
        pupil=pupil,
        schedule=schedule
    )

# ✅ View Attendance
@parent_routes.route("/parent/pupil/<int:pupil_id>/attendance")
def view_attendance(pupil_id):
    """View pupil's attendance records"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)

    # Get attendance records
    attendance_records = Attendance.query.filter_by(pupil_id=pupil_id).all()

    # Calculate stats
    total_days = len(attendance_records)
    present_days = len([a for a in attendance_records if a.status.lower() == "present"])
    absent_days = len([a for a in attendance_records if a.status.lower() == "absent"])

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
        }
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