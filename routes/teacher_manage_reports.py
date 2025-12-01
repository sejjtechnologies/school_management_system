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

    # ------------------------
    # Assign positions per exam (class and stream) and compute combined term results
    # ------------------------
    exam_ids = list(set([r.exam_id for r in reports]))

    # Assign per-exam positions: for each exam, compute positions within each class and within each stream
    class_ids = set(p.class_id for p in assigned_pupils)
    for exam_id in exam_ids:
        for class_id in class_ids:
            # class-level ranking
            class_reports = Report.query.join(Pupil).filter(
                Report.exam_id == exam_id,
                Pupil.class_id == class_id
            ).order_by(Report.total_score.desc()).all()
            for idx, r in enumerate(class_reports, start=1):
                r.class_position = idx

            # stream-level ranking within the class
            stream_ids = set(p.stream_id for p in assigned_pupils if p.class_id == class_id and p.stream_id)
            for stream_id in stream_ids:
                stream_reports = Report.query.join(Pupil).filter(
                    Report.exam_id == exam_id,
                    Pupil.class_id == class_id,
                    Pupil.stream_id == stream_id
                ).order_by(Report.total_score.desc()).all()
                for idx, r in enumerate(stream_reports, start=1):
                    r.stream_position = idx

    db.session.commit()

    # Prepare subject count for averaging across combined exams
    subjects = Subject.query.all()
    subject_count = len(subjects) if subjects else 0

    # Build term -> exam ids mapping for all exams observed
    all_exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()
    term_groups = {}
    for ex in all_exams:
        term_groups.setdefault(ex.term, []).append(ex.id)

    # Combined results per term: compute combined_total and combined_average per pupil,
    # then assign combined positions within class and within stream.
    combined_stats = {}  # pupil_id -> { term -> stats }

    for term, exam_ids_in_term in term_groups.items():
        # gather combined totals for pupils who have reports in these exams
        combined_totals = {}
        for pupil in assigned_pupils:
            reps = Report.query.filter(
                Report.pupil_id == pupil.id,
                Report.exam_id.in_(exam_ids_in_term)
            ).all()
            if not reps:
                continue
            # Weighted combination: Midterm = 40%, End_Term = 60%
            # Fetch exam objects for this term to determine weights per exam id
            exams_objs = Exam.query.filter(Exam.id.in_(exam_ids_in_term)).all()
            # Build initial weights based on exam name heuristics
            weights = {}
            for ex in exams_objs:
                name = (ex.name or "").lower()
                if "mid" in name:
                    weights[ex.id] = 0.4
                elif "end" in name or "end term" in name or "end_term" in name:
                    weights[ex.id] = 0.6
                else:
                    weights[ex.id] = None

            # Normalize weights: assign equal share to any unassigned exams, or fallback to equal weights
            assigned_sum = sum(w for w in weights.values() if w)
            none_count = sum(1 for w in weights.values() if w is None)
            if none_count > 0:
                remaining = max(0.0, 1.0 - assigned_sum)
                per_none = remaining / none_count if none_count else 0
                for k, v in list(weights.items()):
                    if v is None:
                        weights[k] = per_none
            elif assigned_sum == 0 and len(weights) > 0:
                # No explicit mid/end detected; fall back to equal weighting
                for k in weights.keys():
                    weights[k] = 1.0 / len(weights)

            # Compute weighted total across exams for this pupil
            weighted_total = 0.0
            for r in reps:
                w = weights.get(r.exam_id, 0)
                weighted_total += (r.total_score or 0) * w

            # combined average per subject = weighted_total / subject_count
            denom = subject_count if subject_count else 1
            combined_avg = weighted_total / denom
            combined_totals[pupil.id] = {
                'combined_total': round(weighted_total, 2),
                'combined_average': round(combined_avg, 2)
            }

        # Assign combined positions within each class and stream
        # Class-level combined positions
        for class_id in class_ids:
            # pupils in this class who have combined totals
            class_pupil_ids = [pid for pid in combined_totals.keys() if Pupil.query.get(pid).class_id == class_id]
            # sort by combined_average desc
            ranked = sorted(class_pupil_ids, key=lambda pid: combined_totals[pid]['combined_average'], reverse=True)
            for pos, pid in enumerate(ranked, start=1):
                combined_totals[pid]['class_combined_position'] = pos

            # Streams in this class
            stream_ids = set(p.stream_id for p in assigned_pupils if p.class_id == class_id and p.stream_id)
            for stream_id in stream_ids:
                stream_pids = [pid for pid in class_pupil_ids if Pupil.query.get(pid).stream_id == stream_id]
                ranked_stream = sorted(stream_pids, key=lambda pid: combined_totals[pid]['combined_average'], reverse=True)
                for pos, pid in enumerate(ranked_stream, start=1):
                    combined_totals[pid]['stream_combined_position'] = pos

        # Store combined stats back into reports for each pupil and exam in this term
        for pid, stats in combined_totals.items():
            # general remark and combined grade
            gen_remark = calculate_general_remark(stats['combined_average'])
            combined_grade = calculate_grade(stats['combined_average'])

            # update all Report rows for this pupil in the term exams
            reps = Report.query.filter(
                Report.pupil_id == pid,
                Report.exam_id.in_(exam_ids_in_term)
            ).all()
            for rep in reps:
                rep.combined_total = stats['combined_total']
                rep.combined_average = stats['combined_average']
                rep.combined_grade = combined_grade
                rep.general_remark = gen_remark
                rep.combined_position = stats.get('class_combined_position')
                rep.stream_combined_position = stats.get('stream_combined_position')

        # persist for this term
        db.session.commit()

        # save combined_stats snapshot for template use
        for pid, stats in combined_totals.items():
            combined_stats.setdefault(pid, {})[term] = stats

    # Finally prepare lists for template rendering
    subjects = Subject.query.all()
    exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()

    # counts for template: students per stream and per class
    students_per_stream = {}
    students_per_class = {}
    for p in assigned_pupils:
        students_per_stream[p.stream_id] = students_per_stream.get(p.stream_id, 0) + 1
        students_per_class[p.class_id] = students_per_class.get(p.class_id, 0) + 1

    return render_template(
        "teacher/manage_pupils_reports.html",
        teacher=teacher,
        pupils=assigned_pupils,
        reports=reports,
        subjects=subjects,
        exams=exams,
        combined_stats=combined_stats,
        students_per_stream=students_per_stream,
        students_per_class=students_per_class
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