from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from models.user_models import User, Role, db
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from models.register_pupils import Pupil
from models.marks_model import Subject, Exam, Mark, Report

# Blueprint registered as "teacher_routes"
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


@teacher_routes.route("/manage_marks", methods=["GET", "POST"])
def manage_marks():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to manage marks.", "danger")
        return redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    role = Role.query.get(teacher.role_id)
    if not role or role.role_name != "Teacher":
        flash("Access denied.", "danger")
        return redirect(url_for("user_routes.login"))

    success_message = None

    if request.method == "POST":
        pupil_id = request.form["pupil_id"]
        term = int(request.form["term"])
        year = int(request.form["year"])
        exam_name = request.form["exam_name"]  # "Midterm" or "End Term"

        # ✅ Find or create exam record
        exam = Exam.query.filter_by(name=exam_name, term=term, year=year).first()
        if not exam:
            exam = Exam(name=exam_name, term=term, year=year)
            db.session.add(exam)
            db.session.commit()

        # Save marks for all subjects
        subjects = Subject.query.all()
        for subject in subjects:
            score = float(request.form.get(f"score_{subject.id}", 0))
            mark = Mark(pupil_id=pupil_id, subject_id=subject.id, exam_id=exam.id, score=score)
            db.session.add(mark)

        db.session.commit()
        success_message = f"Marks saved successfully for Term {term}, {year} ({exam_name})!"

    pupils = Pupil.query.all()
    subjects = Subject.query.all()
    streams = Stream.query.all()
    classes = Class.query.all()
    years = [2025, 2026, 2027]  # ✅ Example year list

    return render_template("teacher/manage_marks.html",
                           pupils=pupils,
                           subjects=subjects,
                           streams=streams,
                           classes=classes,
                           years=years,
                           success_message=success_message)


@teacher_routes.route("/generate_report/<int:pupil_id>/<int:term>/<int:year>/<exam_name>")
def generate_report(pupil_id, term, year, exam_name):
    exam = Exam.query.filter_by(term=term, year=year, name=exam_name).first_or_404()
    marks = Mark.query.filter_by(pupil_id=pupil_id, exam_id=exam.id).all()
    total_score = sum([m.score for m in marks])
    average_score = total_score / len(marks) if marks else 0

    # Save or update report
    report = Report.query.filter_by(pupil_id=pupil_id, exam_id=exam.id).first()
    if not report:
        report = Report(
            pupil_id=pupil_id,
            exam_id=exam.id,
            total_score=total_score,
            average_score=average_score,
            grade=calculate_grade(average_score),
            remarks="Keep working hard!"
        )
        db.session.add(report)
    else:
        report.total_score = total_score
        report.average_score = average_score
        report.grade = calculate_grade(average_score)
        report.remarks = "Keep working hard!"

    db.session.commit()

    # Positions in stream and class
    pupil = Pupil.query.get_or_404(pupil_id)
    stream_reports = Report.query.join(Pupil).filter(
        Report.exam_id == exam.id,
        Pupil.stream_id == pupil.stream_id
    ).order_by(Report.total_score.desc()).all()

    class_reports = Report.query.join(Pupil).filter(
        Report.exam_id == exam.id,
        Pupil.class_id == pupil.class_id
    ).order_by(Report.total_score.desc()).all()

    stream_position = [r.pupil_id for r in stream_reports].index(pupil_id) + 1
    class_position = [r.pupil_id for r in class_reports].index(pupil_id) + 1

    return render_template("teacher/manage_reports.html",
                           report=report,
                           pupil=pupil,
                           stream_position=stream_position,
                           class_position=class_position)


def calculate_grade(avg):
    if avg >= 80: return "A"
    elif avg >= 70: return "B"
    elif avg >= 60: return "C"
    elif avg >= 50: return "D"
    else: return "E"


@teacher_routes.route("/debug_year")
def debug_year():
    current_year = "2025/26"
    return f"<h2>DEBUG: The current academic year is <strong>{current_year}</strong></h2>"