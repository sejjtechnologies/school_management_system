from flask import Blueprint, render_template, session, redirect, url_for, flash
from models.user_models import User, Role, db
from models.teacher_assignment_models import TeacherAssignment
from models.register_pupils import Pupil
from models.marks_model import Mark, Report, Exam, Subject
from models.class_model import Class   # ✅ Correct file name
from models.stream_model import Stream # ✅ Correct file name

teacher_manage_reports = Blueprint("teacher_manage_reports", __name__, url_prefix="/teacher/reports")


def _require_teacher():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to access this page.", "danger")
        return None, redirect(url_for("user_routes.login"))

    teacher = User.query.get_or_404(user_id)
    role = Role.query.get(teacher.role_id)
    if not role or role.role_name != "Teacher":
        flash("Access denied. Only teachers can view this page.", "danger")
        return None, redirect(url_for("user_routes.login"))

    return teacher, None


def calculate_grade(avg):
    if avg >= 80:
        return "A"
    elif avg >= 70:
        return "B"
    elif avg >= 60:
        return "C"
    elif avg >= 50:
        return "D"
    else:
        return "E"


def calculate_general_remark(avg):
    if avg >= 80:
        return "Outstanding performance overall"
    elif avg >= 70:
        return "Very good work overall"
    elif avg >= 60:
        return "Good effort, keep improving"
    elif avg >= 50:
        return "Fair performance, needs more focus"
    else:
        return "Needs significant improvement"


@teacher_manage_reports.route("/manage", methods=["GET"])
def manage_pupils_reports():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    assigned_pupils = []
    for assignment in assignments:
        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()
        assigned_pupils.extend(pupils)

    reports = []

    for pupil in assigned_pupils:
        # ✅ Attach class and stream names to each pupil
        class_obj = Class.query.get(pupil.class_id)
        stream_obj = Stream.query.get(pupil.stream_id)
        pupil.class_name = class_obj.name if class_obj else f"Class {pupil.class_id}"
        pupil.stream_name = stream_obj.name if stream_obj else f"Stream {pupil.stream_id}"

        marks = Mark.query.filter_by(pupil_id=pupil.id).all()
        if not marks:
            continue

        exam_ids = list(set([m.exam_id for m in marks]))
        for exam_id in exam_ids:
            exam_marks = [m.score for m in marks if m.exam_id == exam_id]
            total_score = sum(exam_marks)
            average_score = total_score / len(exam_marks) if exam_marks else 0
            grade = calculate_grade(average_score)
            remarks = "Keep working hard!" if grade != "A" else "Excellent work!"

            report = Report.query.filter_by(pupil_id=pupil.id, exam_id=exam_id).first()
            if not report:
                report = Report(
                    pupil_id=pupil.id,
                    exam_id=exam_id,
                    total_score=total_score,
                    average_score=average_score,
                    grade=grade,
                    remarks=remarks
                )
                db.session.add(report)
            else:
                report.total_score = total_score
                report.average_score = average_score
                report.grade = grade
                report.remarks = remarks

            reports.append(report)

    db.session.commit()

    # ✅ Assign positions
    for exam_id in set([r.exam_id for r in reports]):
        stream_reports = Report.query.join(Pupil).filter(
            Report.exam_id == exam_id,
            Pupil.stream_id.isnot(None)
        ).order_by(Report.total_score.desc()).all()

        for idx, r in enumerate(stream_reports, start=1):
            r.stream_position = idx

        class_reports = Report.query.join(Pupil).filter(
            Report.exam_id == exam_id
        ).order_by(Report.total_score.desc()).all()

        for idx, r in enumerate(class_reports, start=1):
            r.class_position = idx

    db.session.commit()

    # ✅ Compute combined term performance
    for pupil in assigned_pupils:
        pupil_reports = Report.query.filter(Report.pupil_id == pupil.id).all()
        if not pupil_reports:
            continue

        exam_ids = [r.exam_id for r in pupil_reports]
        exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()

        term_groups = {}
        for exam in exams:
            term_groups.setdefault(exam.term, []).append(exam.id)

        for term, exam_ids_in_term in term_groups.items():
            term_reports = [r for r in pupil_reports if r.exam_id in exam_ids_in_term]
            if not term_reports:
                continue

            avg_term_score = sum([r.average_score for r in term_reports]) / len(term_reports)
            general_remark = calculate_general_remark(avg_term_score)

            # ✅ Attach combined term performance to each report in that term
            for r in term_reports:
                r.general_remark = general_remark
                r.combined_average = avg_term_score
                r.combined_grade = calculate_grade(avg_term_score)

    db.session.commit()

    exam_ids = list(set([r.exam_id for r in reports]))
    subjects = Subject.query.all()
    exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()

    return render_template(
        "teacher/manage_pupils_reports.html",
        teacher=teacher,
        pupils=assigned_pupils,
        reports=reports,
        subjects=subjects,
        exams=exams
    )


@teacher_manage_reports.route("/pupil/<int:pupil_id>", methods=["GET"])
def view_pupil_report(pupil_id):
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    pupil = Pupil.query.get_or_404(pupil_id)
    reports = Report.query.filter_by(pupil_id=pupil.id).all()
    marks = Mark.query.filter_by(pupil_id=pupil.id).all()
    exam_ids = [r.exam_id for r in reports]
    exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()
    subjects = Subject.query.all()

    # ✅ Fetch proper class and stream names
    class_obj = Class.query.get(pupil.class_id)
    stream_obj = Stream.query.get(pupil.stream_id)

    class_name = class_obj.name if class_obj else f"Class {pupil.class_id}"
    stream_name = stream_obj.name if stream_obj else f"Stream {pupil.stream_id}"

    return render_template(
        "teacher/reports.html",
        pupil=pupil,
        reports=reports,
        marks=marks,
        exams=exams,
        subjects=subjects,
        class_name=class_name,
        stream_name=stream_name
    )