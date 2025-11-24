from flask import Blueprint, request, redirect, render_template, flash, session, url_for, jsonify, Response
from werkzeug.security import check_password_hash
from models.user_models import db, User, Role
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from models.register_pupils import Pupil   # ✅ Import pupil model
import os
import csv
import io
from datetime import datetime
import xlsxwriter   # ✅ For Excel export

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

            # ✅ Force Admin accounts to Admin dashboard regardless of DB role drift
            if email.lower() == "sejjtechnologies@gmail.com" or role == "admin":
                return redirect(url_for("user_routes.admin_dashboard"))

            # ✅ Normal routing for other roles
            return redirect(url_for(f"user_routes.{role}_dashboard"))
        else:
            flash("Invalid email or password.", "danger")
            return redirect(url_for("user_routes.login"))

    return render_template("index.html")

@user_routes.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("user_routes.login"))

# Dashboard routes for each role
@user_routes.route("/admin/dashboard")
def admin_dashboard():
    return render_template("admin/dashboard.html")

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

    return render_template("teacher/dashboard.html",
                           teacher=teacher,
                           assignments=assignments,
                           summary=summary,
                           records=all_records)

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
    return Response(output, mimetype="text/csv",
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
            heading = f"School Management System - Teacher: {teacher.first_name} {teacher.last_name} - Year: {current_year} - Class: {assignment.class_.name} - Stream: {assignment.stream.name if assignment.stream else ''}"
            worksheet.write(row, 0, heading, bold)
            row += 1

            headers = ["Admission No.", "First Name", "Middle Name", "Last Name",
                       "Gender", "DOB", "Nationality", "Enrollment Status",
                       "Class", "Stream"]
            for col, h in enumerate(headers):
                worksheet.write(row, col, h, bold)
            row += 1

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

            row += 1  # blank row between assignments

        workbook.close()
        output.seek(0)

        return Response(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
    return Response(output, mimetype="text/csv",
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

    return Response(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment;filename=pupils_details.xlsx"})


# ✅ Other role dashboards
@user_routes.route("/secretary/dashboard")
def secretary_dashboard():
    return render_template("secretary/dashboard.html")

@user_routes.route("/headteacher/dashboard")
def headteacher_dashboard():
    return render_template("headteacher/dashboard.html")

@user_routes.route("/parent/dashboard")
def parent_dashboard():
    return render_template("parent/dashboard.html")

@user_routes.route("/bursar/dashboard")
def bursar_dashboard():
    return render_template("bursar/dashboard.html")