from flask import Blueprint, request, redirect, render_template, flash, session, url_for, Response
from werkzeug.security import check_password_hash
from models.user_models import db, User, Role, AdminSession
from models.salary_models import RoleSalary
from models.teacher_assignment_models import TeacherAssignment
from models.register_pupils import Pupil   # ✅ Import pupil model
import csv
import io
from datetime import datetime
import secrets
try:
    import xlsxwriter  # type: ignore
except Exception as e:
    raise RuntimeError(
        "Missing dependency: xlsxwriter is required for Excel export routes. "
        "Install in your virtualenv with 'python -m pip install xlsxwriter'."
    ) from e

user_routes = Blueprint("user_routes", __name__)

# ✅ Map of default roles to enforce correct role_id
DEFAULT_ROLES = {
    "admin": "Admin",
    "teacher": "Teacher",
    "secretary": "Secretary",
    "headteacher": "Headteacher",
    "parent": "Parent",
    "bursar": "Bursar"
}

@user_routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(email=email).first()

        # ✅ Debug print to terminal
        print("Login attempt:", email,
              "User found:", user,
              "Password check:", check_password_hash(user.password, password) if user else None,
              "Role:", user.role.role_name if user else None)

        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["role"] = user.role.role_name
            session.permanent = remember

            role = user.role.role_name.lower()

            # ✅ Auto-correct role drift for all default roles
            if role in DEFAULT_ROLES:
                correct_role = Role.query.filter_by(role_name=DEFAULT_ROLES[role]).first()
                if correct_role and user.role_id != correct_role.id:
                    user.role_id = correct_role.id
                    db.session.commit()
                    print(f"✅ Corrected {DEFAULT_ROLES[role]} role_id in DB for", email)

            # ✅ ADMIN SESSION MANAGEMENT: Enforce single-device login for Admin role
            if role == "admin":
                # Invalidate previous session if exists
                if user.active_session_id:
                    old_session = AdminSession.query.filter_by(
                        session_id=user.active_session_id
                    ).first()
                    if old_session:
                        old_session.is_active = False
                        db.session.commit()
                        print(f"✅ Invalidated previous admin session: {old_session.session_id[:8]}...")

                # Create new admin session
                new_session_id = secrets.token_urlsafe(32)
                ip_address = request.remote_addr
                user_agent = request.headers.get("User-Agent", "")[:255]

                admin_session = AdminSession(
                    user_id=user.id,
                    session_id=new_session_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    is_active=True
                )
                user.active_session_id = new_session_id
                session["active_session_id"] = new_session_id  # ✅ Store in Flask session too
                db.session.add(admin_session)
                db.session.commit()
                print(f"✅ Created new admin session: {new_session_id[:8]}... from IP {ip_address}")
                flash(f"Admin login successful from {ip_address}. Previous sessions invalidated.", "info")

            # ✅ Force Admin accounts to Admin dashboard regardless of DB role drift
            if email.lower() == "sejjtechnologies@gmail.com" or role == "admin":
                # ✅ Redirect to avoid resubmission warning
                return redirect(url_for("user_routes.admin_dashboard"))

            # ✅ Normal routing for other roles
            return redirect(url_for(f"user_routes.{role}_dashboard"))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("user_routes.login"))

    return render_template("index.html")

@user_routes.route("/logout")
def logout():
    user_id = session.get("user_id")
    role = session.get("role")

    # ✅ Invalidate admin session if admin is logging out
    if role and role.lower() == "admin" and user_id:
        user = User.query.get(user_id)
        if user and user.active_session_id:
            admin_session = AdminSession.query.filter_by(
                session_id=user.active_session_id
            ).first()
            if admin_session:
                admin_session.is_active = False
                db.session.commit()
                print(f"✅ Admin session deactivated on logout: {admin_session.session_id[:8]}...")
            user.active_session_id = None
            db.session.commit()

    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("user_routes.login"))

# ✅ API ENDPOINT: Check if admin session is still valid (for real-time logout detection)
@user_routes.route("/api/check-session", methods=["GET"])
def check_session():
    """Check if current admin session is still active. Used for real-time logout detection."""
    user_id = session.get("user_id")
    role = session.get("role")
    client_session_id = session.get("active_session_id")

    # Only for admin users
    if not (role and role.lower() == "admin" and user_id and client_session_id):
        return {"valid": False, "message": "Not an admin session"}, 401

    try:
        user = User.query.get(user_id)

        # Check if user exists
        if not user:
            return {"valid": False, "message": "User account deleted"}, 401

        # ✅ KEY CHECK: Compare client session ID with DB's active session ID
        if user.active_session_id != client_session_id:
            return {
                "valid": False,
                "message": "Session conflict - logged in from another device",
                "reason": "multi_device_login"
            }, 401

        # Check if session is still active in DB
        admin_session = AdminSession.query.filter_by(
            session_id=client_session_id,
            user_id=user_id
        ).first()

        if not admin_session or not admin_session.is_active:
            return {
                "valid": False,
                "message": "Session inactive - logged in from another device",
                "reason": "session_inactive"
            }, 401

        # Session is valid
        return {
            "valid": True,
            "user_id": user_id,
            "message": "Session is active"
        }, 200

    except Exception as e:
        print(f"[ERROR] Session check failed: {str(e)}")
        return {"valid": False, "message": "Session validation error"}, 500

# Dashboard routes for each role
@user_routes.route("/admin/dashboard")
def admin_dashboard():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to access the admin dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    admin = User.query.get_or_404(user_id)
    role = Role.query.get(admin.role_id)
    if not role or role.role_name != "Admin":
        flash("Access denied. Only admins can view this dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    # ✅ Pass admin object safely
    return render_template("admin/dashboard.html", admin=admin)

@user_routes.route("/teacher/dashboard")
def teacher_dashboard():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to access the teacher dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    role = Role.query.get(teacher.role_id)
    if not role or role.role_name != "Teacher":
        flash("Access denied. Only teachers can view this dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not assignments:
        return render_template("teacher/no_assignment.html", teacher=teacher)

    all_records = []
    summary = []
    for assignment in assignments:
        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()

        student_count = len(pupils)
        summary.append({
            "class": assignment.class_.name,
            "stream": assignment.stream.name if assignment.stream else None,
            "student_count": student_count
        })
        all_records.extend(pupils)

    current_year = "2025/26"

    # ✅ Add these lists so templates don’t break
    terms = [1, 2, 3]
    years = [2025, 2026, 2027]
    exam_types = ["Midterm", "End Term"]

    return render_template("teacher/dashboard.html",
                           teacher=teacher,
                           assignments=assignments,
                           summary=summary,
                           records=all_records,
                           current_year=current_year,
                           terms=terms,
                           years=years,
                           exam_types=exam_types)

# ✅ Export pupils to CSV
@user_routes.route("/teacher/export_csv")
def teacher_export_csv():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in.", "danger")
        return redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not assignments:
        flash("No assignments found.", "warning")
        return redirect(url_for("user_routes.teacher_dashboard"))

    output = io.StringIO()
    writer = csv.writer(output)
    current_year = datetime.now().year

    for assignment in assignments:
        heading = f"School Management System - Teacher: {teacher.first_name} {teacher.last_name} - Year: {current_year} - Class: {assignment.class_.name} - Stream: {assignment.stream.name if assignment.stream else ''}"
        writer.writerow([heading])
        writer.writerow(["Admission No.", "First Name", "Middle Name", "Last Name",
                         "Gender", "DOB", "Nationality", "Enrollment Status",
                         "Class", "Stream"])

        pupils = Pupil.query.filter_by(class_id=assignment.class_id,
                                       stream_id=assignment.stream_id).all()
        for p in pupils:
            writer.writerow([
                p.admission_number, p.first_name, p.middle_name, p.last_name,
                p.gender, p.dob, p.nationality, p.enrollment_status,
                assignment.class_.name, assignment.stream.name if assignment.stream else None
            ])
        writer.writerow([])

    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=class_list.csv"})


@user_routes.route("/teacher/export_excel")
def teacher_export_excel():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in.", "danger")
        return redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not assignments:
        flash("No assignments found.", "warning")
        return redirect(url_for("user_routes.teacher_dashboard"))

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Class List")

    bold = workbook.add_format({'bold': True})
    current_year = datetime.now().year
    row = 0

    for assignment in assignments:
        heading = (
            f"School Management System - Teacher: {teacher.first_name} {teacher.last_name} - "
            f"Year: {current_year} - Class: {assignment.class_.name} - "
            f"Stream: {assignment.stream.name if assignment.stream else ''}"
        )
        worksheet.write(row, 0, heading, bold)
        row += 1

        headers = [
            "Admission No.", "First Name", "Middle Name", "Last Name",
            "Gender", "DOB", "Nationality", "Enrollment Status",
            "Class", "Stream"
        ]
        for col, h in enumerate(headers):
            worksheet.write(row, col, h, bold)
        row += 1

        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()

        for p in pupils:
            dob_val = ''
            try:
                dob_val = p.dob.strftime('%Y-%m-%d') if p.dob else ''
            except Exception:
                dob_val = str(p.dob) if p.dob else ''

            worksheet.write(row, 0, p.admission_number)
            worksheet.write(row, 1, p.first_name)
            worksheet.write(row, 2, p.middle_name)
            worksheet.write(row, 3, p.last_name)
            worksheet.write(row, 4, p.gender)
            worksheet.write(row, 5, dob_val)
            worksheet.write(row, 6, p.nationality)
            worksheet.write(row, 7, p.enrollment_status)
            worksheet.write(row, 8, assignment.class_.name)
            worksheet.write(row, 9, assignment.stream.name if assignment.stream else None)
            row += 1

        row += 1  # blank row between assignments

    workbook.close()
    output.seek(0)
    data = output.getvalue()
    return Response(data,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment;filename=class_list.xlsx"})

# ✅ Pupils Details route
@user_routes.route("/teacher/pupils_details")
def pupils_details():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to view pupils details.", "danger")
        return redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    role = Role.query.get(teacher.role_id)
    if not role or role.role_name != "Teacher":
        flash("Access denied. Only teachers can view pupils details.", "danger")
        return redirect(url_for("user_routes.login"))

    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not assignments:
        return render_template("teacher/no_assignment.html", teacher=teacher)

    records = []
    for assignment in assignments:
        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()
        records.extend(pupils)

    return render_template("teacher/pupils_details.html",
                           teacher=teacher,
                           records=records)

# ✅ Export all pupils (from pupils_details) to CSV
@user_routes.route("/teacher/pupils_export_csv")
def pupils_export_csv():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in.", "danger")
        return redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not assignments:
        flash("No assignments found.", "warning")
        return redirect(url_for("user_routes.teacher_dashboard"))

    output = io.StringIO()
    writer = csv.writer(output)
    current_year = datetime.now().year

    writer.writerow([f"School Management System - Pupils Details Export - Teacher: {teacher.first_name} {teacher.last_name} - Year: {current_year}"])
    writer.writerow(["Admission No.", "First Name", "Middle Name", "Last Name",
                     "Gender", "DOB", "Nationality", "Enrollment Status",
                     "Class", "Stream"])

    for assignment in assignments:
        pupils = Pupil.query.filter_by(class_id=assignment.class_id,
                                       stream_id=assignment.stream_id).all()
        for p in pupils:
            writer.writerow([
                p.admission_number, p.first_name, p.middle_name, p.last_name,
                p.gender, p.dob, p.nationality, p.enrollment_status,
                assignment.class_.name, assignment.stream.name if assignment.stream else None
            ])

    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=pupils_details.csv"})

# ✅ Export all pupils (from pupils_details) to Excel
@user_routes.route("/teacher/pupils_export_excel")
def pupils_export_excel():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in.", "danger")
        return redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not assignments:
        flash("No assignments found.", "warning")
        return redirect(url_for("user_routes.teacher_dashboard"))

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("All Pupils")

    bold = workbook.add_format({'bold': True})
    current_year = datetime.now().year
    row = 0

    worksheet.write(row, 0, f"School Management System - Pupils Details Export - Teacher: {teacher.first_name} {teacher.last_name} - Year: {current_year}", bold)
    row += 2

    headers = ["Admission No.", "First Name", "Middle Name", "Last Name",
               "Gender", "DOB", "Nationality", "Enrollment Status",
               "Class", "Stream"]
    for col, h in enumerate(headers):
        worksheet.write(row, col, h, bold)
    row += 1

    for assignment in assignments:
        pupils = Pupil.query.filter_by(class_id=assignment.class_id,
                                       stream_id=assignment.stream_id).all()
        for p in pupils:
            worksheet.write(row, 0, p.admission_number)
            worksheet.write(row, 1, p.first_name)
            worksheet.write(row, 2, p.middle_name)
            worksheet.write(row, 3, p.last_name)
            worksheet.write(row, 4, p.gender)
            worksheet.write(row, 5, str(p.dob))
            worksheet.write(row, 6, p.nationality)
            worksheet.write(row, 7, p.enrollment_status)
            worksheet.write(row, 8, assignment.class_.name)
            worksheet.write(row, 9, assignment.stream.name if assignment.stream else None)
            row += 1

    workbook.close()
    output.seek(0)

    return Response(output.getvalue(), mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment;filename=pupils_details.xlsx"})

# ✅ Other role dashboards
@user_routes.route("/secretary/dashboard")
def secretary_dashboard():
    return render_template("secretary/dashboard.html")

@user_routes.route("/headteacher/dashboard")
def headteacher_dashboard():
    # Provide role salary defaults to the template so the staff table can show role-based salaries
    role_salaries = []
    try:
        rs_rows = RoleSalary.query.join(Role, RoleSalary.role_id == Role.id).all()
        for r in rs_rows:
            role_salaries.append({
                'id': r.id,
                'role_id': r.role_id,
                'role_name': getattr(r.role, 'role_name', None),
                'amount': str(r.amount) if getattr(r, 'amount', None) is not None else None,
            })
    except Exception:
        role_salaries = []
    return render_template("headteacher/dashboard.html", role_salaries=role_salaries)

@user_routes.route("/parent/dashboard")
def parent_dashboard():
    return render_template("parent/dashboard.html")

@user_routes.route("/bursar/dashboard")
def bursar_dashboard():
    return render_template("bursar/dashboard.html")