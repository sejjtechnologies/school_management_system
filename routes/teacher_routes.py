from flask import Blueprint, render_template, session, flash, redirect, url_for
from models.user_models import User, Role
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from models.register_pupils import Pupil

teacher_routes = Blueprint("teacher_routes", __name__, url_prefix="/teacher")

@teacher_routes.route("/dashboard")
def dashboard():
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

    records = []
    for assignment in assignments:
        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()
        records.extend(pupils)

    current_year = "2025/26"

    return render_template("teacher/dashboard.html",
                           teacher=teacher,
                           assignments=assignments,
                           records=records,
                           current_year=current_year)


@teacher_routes.route("/pupils_details")
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
    records = []
    for assignment in assignments:
        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()
        records.extend(pupils)

    current_year = "2025/26"

    return render_template("teacher/pupils_details.html",
                           teacher=teacher,
                           records=records,
                           current_year=current_year)


@teacher_routes.route("/debug_year")
def debug_year():
    current_year = "2025/26"
    return f"<h2>DEBUG: The current academic year is <strong>{current_year}</strong></h2>"