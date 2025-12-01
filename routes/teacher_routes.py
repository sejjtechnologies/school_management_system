from flask import Blueprint, render_template, session, flash, redirect, url_for, request
from models.user_models import User, Role, db
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from models.register_pupils import Pupil
from models.marks_model import Subject, Exam, Mark, Report

# Blueprint registered as "teacher_routes"
teacher_routes = Blueprint("teacher_routes", __name__, url_prefix="/teacher")


def _require_teacher():
    """Return (teacher, redirect_response) where redirect_response is None when OK."""
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


@teacher_routes.route("/dashboard")
def dashboard():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

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

    terms = [1, 2, 3]
    years = [2025, 2026, 2027]
    exam_types = ["Midterm", "End_Term"]

    return render_template("teacher/dashboard.html",
                           teacher=teacher,
                           assignments=assignments,
                           records=records,
                           current_year=current_year,
                           terms=terms,
                           years=years,
                           exam_types=exam_types)


@teacher_routes.route("/pupils_details")
def pupils_details():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

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
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    success_message = None

    if request.method == "POST":
        try:
            pupil_id = int(request.form["pupil_id"])
        except (KeyError, ValueError):
            flash("Invalid pupil selected.", "danger")
            return redirect(url_for("teacher_routes.manage_marks"))

        term = int(request.form.get("term", 0))
        year = int(request.form.get("year", 0))
        exam_name = request.form.get("exam_name", "").strip().replace(" ", "_")

        exam = Exam.query.filter_by(name=exam_name, term=term, year=year).first()
        if not exam:
            exam = Exam(name=exam_name, term=term, year=year)
            db.session.add(exam)
            db.session.commit()

        subjects = Subject.query.all()
        for subject in subjects:
            raw = request.form.get(f"score_{subject.id}", "")
            try:
                score = float(raw) if raw != "" else 0.0
            except ValueError:
                score = 0.0

            # ✅ FIX: update existing mark instead of duplicating
            existing_mark = Mark.query.filter_by(
                pupil_id=pupil_id,
                subject_id=subject.id,
                exam_id=exam.id
            ).first()

            if existing_mark:
                existing_mark.score = score
            else:
                new_mark = Mark(
                    pupil_id=pupil_id,
                    subject_id=subject.id,
                    exam_id=exam.id,
                    score=score
                )
                db.session.add(new_mark)

        db.session.commit()

        # ✅ Redirect to correct endpoint in teacher_manage_reports blueprint
        return redirect(url_for("teacher_manage_reports.manage_pupils_reports"))

    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    records = []
    for assignment in assignments:
        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()
        records.extend(pupils)

    pupils = records
    subjects = Subject.query.all()
    streams = Stream.query.all()
    classes = Class.query.all()

    years = [2025, 2026, 2027]
    terms = [1, 2, 3]
    exam_types = ["Midterm", "End_Term"]

    # ✅ Updated to point to manage_pupils_marks.html
    return render_template("teacher/manage_pupils_marks.html",
                           pupils=pupils,
                           subjects=subjects,
                           streams=streams,
                           classes=classes,
                           years=years,
                           terms=terms,
                           exam_types=exam_types,
                           success_message=success_message)

@teacher_routes.route("/generate_report/<int:pupil_id>/<int:term>/<int:year>/<string:exam_name>")
def generate_report(pupil_id, term, year, exam_name):
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    allowed_pupil_ids = []
    for assignment in assignments:
        pupils = Pupil.query.filter_by(
            class_id=assignment.class_id,
            stream_id=assignment.stream_id
        ).all()
        allowed_pupil_ids.extend([p.id for p in pupils])

    if pupil_id not in allowed_pupil_ids:
        flash("Access denied. This pupil is not assigned to you.", "danger")
        return redirect(url_for("teacher_routes.dashboard"))

    exam_name = exam_name.replace(" ", "_")

    exam = Exam.query.filter_by(term=term, year=year, name=exam_name).first_or_404()
    marks = Mark.query.filter_by(pupil_id=pupil_id, exam_id=exam.id).all()
    total_score = sum([m.score for m in marks])
    average_score = total_score / len(marks) if marks else 0

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

    pupil = Pupil.query.get_or_404(pupil_id)

    # ✅ Fetch proper class and stream names
    class_obj = Class.query.get(pupil.class_id)
    stream_obj = Stream.query.get(pupil.stream_id)
    class_name = class_obj.name if class_obj else f"Class {pupil.class_id}"
    stream_name = stream_obj.name if stream_obj else f"Stream {pupil.stream_id}"

    stream_reports = Report.query.join(Pupil).filter(
        Report.exam_id == exam.id,
        Pupil.stream_id == pupil.stream_id
    ).order_by(Report.total_score.desc()).all()

    class_reports = Report.query.join(Pupil).filter(
        Report.exam_id == exam.id,
        Pupil.class_id == pupil.class_id
    ).order_by(Report.total_score.desc()).all()

    stream_position = [r.pupil_id for r in stream_reports].index(pupil_id) + 1 if stream_reports else 0
    class_position = [r.pupil_id for r in class_reports].index(pupil_id) + 1 if class_reports else 0

    # Also compute combined-term stats (e.g., Midterm + End_Term) for this term/year
    exam_ids_in_term = [e.id for e in Exam.query.filter_by(term=term, year=year).all()]
    subjects = Subject.query.all()
    subject_count = len(subjects) if subjects else 0

    # pupils in same class (we rank across class and stream)
    pupils_in_class = Pupil.query.filter_by(class_id=pupil.class_id).all()

    combined_totals = {}
    # Weighted combination: Midterm = 40%, End_Term = 60%
    exams_objs = Exam.query.filter(Exam.id.in_(exam_ids_in_term)).all()
    weights = {}
    for ex in exams_objs:
        name = (ex.name or "").lower()
        if "mid" in name:
            weights[ex.id] = 0.4
        elif "end" in name or "end term" in name or "end_term" in name:
            weights[ex.id] = 0.6
        else:
            weights[ex.id] = None

    assigned_sum = sum(w for w in weights.values() if w)
    none_count = sum(1 for w in weights.values() if w is None)
    if none_count > 0:
        remaining = max(0.0, 1.0 - assigned_sum)
        per_none = remaining / none_count if none_count else 0
        for k in weights.keys():
            if weights[k] is None:
                weights[k] = per_none
    elif assigned_sum == 0 and len(weights) > 0:
        for k in weights.keys():
            weights[k] = 1.0 / len(weights)

    for p in pupils_in_class:
        reps = Report.query.filter(Report.pupil_id == p.id, Report.exam_id.in_(exam_ids_in_term)).all()
        if not reps:
            continue
        weighted_total = 0.0
        for r in reps:
            w = weights.get(r.exam_id, 0)
            weighted_total += (r.total_score or 0) * w

        denom = subject_count if subject_count else 1
        combined_avg = round((weighted_total / denom), 2)
        combined_totals[p.id] = {
            'combined_total': round(weighted_total, 2),
            'combined_average': combined_avg
        }

    # Assign combined positions within class and within stream
    # Class-level ranking
    class_ranked = sorted(combined_totals.keys(), key=lambda pid: combined_totals[pid]['combined_average'], reverse=True)
    class_positions = {pid: idx+1 for idx, pid in enumerate(class_ranked)}

    # Stream-level ranking (within class)
    stream_pupils = [p.id for p in pupils_in_class if p.stream_id == pupil.stream_id]
    stream_ranked = sorted([pid for pid in stream_pupils if pid in combined_totals], key=lambda pid: combined_totals[pid]['combined_average'], reverse=True)
    stream_positions = {pid: idx+1 for idx, pid in enumerate(stream_ranked)}

    # Attach combined stats into a dict for the template
    combined_stats = {}
    for pid, stats in combined_totals.items():
        stats['class_combined_position'] = class_positions.get(pid)
        stats['stream_combined_position'] = stream_positions.get(pid)
        stats['combined_grade'] = calculate_grade(stats['combined_average'])
        stats['general_remark'] = calculate_general_remark(stats['combined_average'])
        combined_stats[pid] = stats

    # counts
    students_per_stream = {}
    students_per_class = {pupil.class_id: len(pupils_in_class)}
    for p in pupils_in_class:
        students_per_stream[p.stream_id] = students_per_stream.get(p.stream_id, 0) + 1

    print("DEBUG: Rendering template teacher/manage_pupils_reports.html")
    return render_template("teacher/manage_pupils_reports.html",
                           reports=[report] if report else [],
                           selected_pupil=pupil,
                           selected_term=term,
                           selected_year=year,
                           selected_exam_name=exam_name,
                           teacher=teacher,
                           stream_position=stream_position,
                           class_position=class_position,
                           class_name=class_name,
                           stream_name=stream_name,
                           combined_stats=combined_stats,
                           students_per_stream=students_per_stream,
                           students_per_class=students_per_class)


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


@teacher_routes.route("/debug_year")
def debug_year():
    current_year = "2025/26"
    return f"<h2>DEBUG: The current academic year is <strong>{current_year}</strong></h2>"


# ✅ Extra debug route to list all templates Flask can see
from flask import current_app as app

@teacher_routes.route("/debug_templates")
def debug_templates():
    templates = app.jinja_env.list_templates()
    return "<h2>Templates Flask can see:</h2><ul>" + "".join(
        f"<li>{t}</li>" for t in sorted(templates)
    ) + "</ul>"