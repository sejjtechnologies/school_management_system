from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from sqlalchemy import or_, and_
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
    # build a single query to fetch all pupils assigned to this teacher (match class+stream pairs)
    assigned_pupils = []
    if assignments:
        filters = [and_(Pupil.class_id == a.class_id, Pupil.stream_id == a.stream_id) for a in assignments]
        if filters:
            assigned_pupils = Pupil.query.filter(or_(*filters)).all()

    # --- Optimize data access: batch queries and in-memory grouping to avoid N+1 queries ---
    reports = []

    # Pagination parameters (server-side)
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 50))
    except ValueError:
        per_page = 50

    if not assigned_pupils:
        # Nothing assigned
        return render_template(
            "teacher/manage_pupils_reports.html",
            teacher=teacher,
            pupils=[],
            reports=reports,
            subjects=[],
            exams=[],
            combined_stats={},
            students_per_stream={},
            students_per_class={},
            page=page,
            per_page=per_page,
            total=0
        )

    total_assigned = len(assigned_pupils)
    total_pages = max(1, (total_assigned + per_page - 1) // per_page)
    # clamp page
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    paged_assigned_pupils = assigned_pupils[start:end]

    assigned_ids = [p.id for p in assigned_pupils]

    # Prefetch classes and streams for name lookups
    class_ids = list(set(p.class_id for p in assigned_pupils if p.class_id))
    stream_ids = list(set(p.stream_id for p in assigned_pupils if p.stream_id))
    class_map = {c.id: c for c in Class.query.filter(Class.id.in_(class_ids)).all()} if class_ids else {}
    stream_map = {s.id: s for s in Stream.query.filter(Stream.id.in_(stream_ids)).all()} if stream_ids else {}

    # Prefetch all marks for the assigned pupils in one query
    marks = Mark.query.filter(Mark.pupil_id.in_(assigned_ids)).all()
    marks_by_pupil = {}
    for m in marks:
        marks_by_pupil.setdefault(m.pupil_id, []).append(m)

    # Prefetch existing reports for these pupils to avoid per-row DB lookups
    existing_reports = Report.query.filter(Report.pupil_id.in_(assigned_ids)).all()
    report_map = {(r.pupil_id, r.exam_id): r for r in existing_reports}

    # Build a pupil id -> pupil object map for cheap lookups
    pupil_map = {p.id: p for p in assigned_pupils}

    # Compute per-pupil reports based on marks_by_pupil using the prefetched data
    for pupil in assigned_pupils:
        # Attach class and stream names from maps
        class_obj = class_map.get(pupil.class_id)
        stream_obj = stream_map.get(pupil.stream_id)
        pupil.class_name = class_obj.name if class_obj else (f"Class {pupil.class_id}" if pupil.class_id else 'N/A')
        pupil.stream_name = stream_obj.name if stream_obj else (f"Stream {pupil.stream_id}" if pupil.stream_id else 'N/A')

        pm = marks_by_pupil.get(pupil.id, [])
        if not pm:
            continue

        exam_ids_for_pupil = list({m.exam_id for m in pm})
        for exam_id in exam_ids_for_pupil:
            exam_marks = [m.score for m in pm if m.exam_id == exam_id]
            total_score = sum(exam_marks)
            average_score = total_score / len(exam_marks) if exam_marks else 0
            grade = calculate_grade(average_score)
            remarks = "Keep working hard!" if grade != "A" else "Excellent work!"

            key = (pupil.id, exam_id)
            report = report_map.get(key)
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
                # add to map so subsequent logic can see it
                report_map[key] = report
            else:
                report.total_score = total_score
                report.average_score = average_score
                report.grade = grade
                report.remarks = remarks

            reports.append(report)

    db.session.commit()

    # Assign per-exam positions using in-memory grouping (avoid new DB queries in loop)
    exam_ids = list(set([r.exam_id for r in reports]))
    class_ids = set(p.class_id for p in assigned_pupils if p.class_id)

    # build reports_by_exam for quick access
    reports_by_exam = {}
    for r in reports:
        reports_by_exam.setdefault(r.exam_id, []).append(r)

    # build pupil lookup for class/stream info (we may need full class lists later)
    # For class-wide computations we'll fetch full class lists below when needed
    for exam_id in exam_ids:
        exam_reports = reports_by_exam.get(exam_id, [])
        # class-level ranking
        for class_id in class_ids:
            class_reports = [r for r in exam_reports if pupil_map.get(r.pupil_id) and pupil_map[r.pupil_id].class_id == class_id]
            class_reports.sort(key=lambda x: (x.total_score or 0), reverse=True)
            for idx, r in enumerate(class_reports, start=1):
                r.class_position = idx

            # stream-level within this class (streams that this teacher has in this class)
            stream_ids_in_class = set(p.stream_id for p in assigned_pupils if p.class_id == class_id and p.stream_id)
            for stream_id in stream_ids_in_class:
                stream_reports = [r for r in class_reports if pupil_map.get(r.pupil_id) and pupil_map[r.pupil_id].stream_id == stream_id]
                for idx, r in enumerate(stream_reports, start=1):
                    r.stream_position = idx

    db.session.commit()

    # Prepare subject count for averaging across combined exams
    subjects = Subject.query.all()
    subject_count = len(subjects) if subjects else 0

    # Build pupils per class map for classes we care about (class-wide computations)
    pupils_by_class = {}
    classes_to_check = set(p.class_id for p in assigned_pupils if p.class_id)
    for cid in classes_to_check:
        pupils_by_class[cid] = Pupil.query.filter_by(class_id=cid).all()

    # Build reports_by_pupil for quick lookup
    reports_by_pupil = {}
    for r in reports:
        reports_by_pupil.setdefault(r.pupil_id, []).append(r)

    # Build a quick map of a representative report per pupil (first one) for template fallback
    report_map = {pid: reps[0] for pid, reps in reports_by_pupil.items() if reps}

    # Build term -> exam ids mapping for all exams observed in reports
    all_exam_objs = Exam.query.filter(Exam.id.in_(exam_ids)).all() if exam_ids else []
    term_groups = {}
    for ex in all_exam_objs:
        term_groups.setdefault(ex.term, []).append(ex.id)

    combined_stats = {}

    for term, exam_ids_in_term in term_groups.items():
        # fetch exam objects once
        exams_objs = [ex for ex in all_exam_objs if ex.id in exam_ids_in_term]
        # determine weights template
        weights_template = {}
        for ex in exams_objs:
            name = (ex.name or "").lower()
            if "mid" in name:
                weights_template[ex.id] = 0.4
            elif "end" in name or "end term" in name or "end_term" in name:
                weights_template[ex.id] = 0.6
            else:
                weights_template[ex.id] = None

        assigned_sum = sum(w for w in weights_template.values() if w)
        none_count = sum(1 for w in weights_template.values() if w is None)
        if none_count > 0:
            remaining = max(0.0, 1.0 - assigned_sum)
            per_none = remaining / none_count if none_count else 0
            for k in list(weights_template.keys()):
                if weights_template[k] is None:
                    weights_template[k] = per_none
        elif assigned_sum == 0 and len(weights_template) > 0:
            for k in weights_template.keys():
                weights_template[k] = 1.0 / len(weights_template)

        # compute combined totals for each class and their pupils
        combined_totals = {}
        for class_id, pupils_in_class_full in pupils_by_class.items():
            for p in pupils_in_class_full:
                reps = [r for r in reports_by_pupil.get(p.id, []) if r.exam_id in exam_ids_in_term]
                if not reps:
                    continue
                weighted_total = 0.0
                for r in reps:
                    w = weights_template.get(r.exam_id, 0)
                    weighted_total += (r.total_score or 0) * w
                denom = subject_count if subject_count else 1
                combined_avg = weighted_total / denom
                combined_totals[p.id] = {
                    'combined_total': round(weighted_total, 2),
                    'combined_average': round(combined_avg, 2)
                }

        # assign class and stream combined positions
        for class_id, pupils_in_class_full in pupils_by_class.items():
            class_pids = [pid for pid in combined_totals.keys() if (pupil_map.get(pid) and pupil_map[pid].class_id == class_id) or any(p.id == pid for p in pupils_in_class_full)]
            # ensure we only consider pids that have combined_totals
            class_pids = [pid for pid in class_pids if pid in combined_totals]
            ranked = sorted(class_pids, key=lambda pid: combined_totals[pid]['combined_average'], reverse=True)
            for pos, pid in enumerate(ranked, start=1):
                combined_totals[pid]['class_combined_position'] = pos

            # streams in this class
            stream_ids_in_class = set(p.stream_id for p in pupils_in_class_full if p.stream_id)
            for stream_id in stream_ids_in_class:
                stream_pids = [pid for pid in ranked if (pupil_map.get(pid) and pupil_map[pid].stream_id == stream_id) or any(p.id == pid for p in pupils_in_class_full if p.stream_id == stream_id)]
                # filter only those with combined_totals
                stream_pids = [pid for pid in stream_pids if pid in combined_totals]
                for pos, pid in enumerate(stream_pids, start=1):
                    combined_totals[pid]['stream_combined_position'] = pos

        # update Report rows for pupils in this term
        for pid, stats in combined_totals.items():
            gen_remark = calculate_general_remark(stats['combined_average'])
            combined_grade = calculate_grade(stats['combined_average'])
            reps = [r for r in reports_by_pupil.get(pid, []) if r.exam_id in exam_ids_in_term]
            for rep in reps:
                rep.combined_total = stats['combined_total']
                rep.combined_average = stats['combined_average']
                rep.combined_grade = combined_grade
                rep.general_remark = gen_remark
                rep.combined_position = stats.get('class_combined_position')
                rep.stream_combined_position = stats.get('stream_combined_position')

        db.session.commit()

        # persist snapshot for template
        for pid, stats in combined_totals.items():
            combined_stats.setdefault(pid, {})[term] = stats

    # Finally prepare lists for template rendering
    subjects = Subject.query.all()
    exams = Exam.query.filter(Exam.id.in_(exam_ids)).all() if exam_ids else []

    # counts for template: students per stream and per class
    students_per_stream = {}
    students_per_class = {}
    for cid, pupils_in_class_full in pupils_by_class.items():
        students_per_class[cid] = len(pupils_in_class_full)
        for p in pupils_in_class_full:
            students_per_stream[p.stream_id] = students_per_stream.get(p.stream_id, 0) + 1
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
        # NOTE: compute across the whole class (all pupils in each class), not only those
        # assigned to this teacher, so positions are class-wide.
        combined_totals = {}
        # fetch exam objects for this term once
        exams_objs = Exam.query.filter(Exam.id.in_(exam_ids_in_term)).all()
        # Build initial weights based on exam name heuristics
        weights_template = {}
        for ex in exams_objs:
            name = (ex.name or "").lower()
            if "mid" in name:
                weights_template[ex.id] = 0.4
            elif "end" in name or "end term" in name or "end_term" in name:
                weights_template[ex.id] = 0.6
            else:
                weights_template[ex.id] = None

        # Normalize weights template: assign equal share to any unassigned exams, or fallback to equal weights
        assigned_sum = sum(w for w in weights_template.values() if w)
        none_count = sum(1 for w in weights_template.values() if w is None)
        if none_count > 0:
            remaining = max(0.0, 1.0 - assigned_sum)
            per_none = remaining / none_count if none_count else 0
            for k in list(weights_template.keys()):
                if weights_template[k] is None:
                    weights_template[k] = per_none
        elif assigned_sum == 0 and len(weights_template) > 0:
            for k in weights_template.keys():
                weights_template[k] = 1.0 / len(weights_template)

        # For each class that the teacher is assigned to, compute combined averages for all pupils in that class
        for class_id in class_ids:
            pupils_in_class_full = Pupil.query.filter_by(class_id=class_id).all()
            for pupil in pupils_in_class_full:
                reps = Report.query.filter(
                    Report.pupil_id == pupil.id,
                    Report.exam_id.in_(exam_ids_in_term)
                ).all()
                if not reps:
                    continue
                # Compute weighted total across exams for this pupil
                weighted_total = 0.0
                for r in reps:
                    w = weights_template.get(r.exam_id, 0)
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
            # use pupils_by_class map to avoid querying Pupil.get repeatedly
            class_pupil_ids = [pid for pid in combined_totals.keys() if pid in combined_totals and any(p.id == pid for p in pupils_by_class.get(class_id, []))]
            # sort by combined_average desc
            ranked = sorted(class_pupil_ids, key=lambda pid: combined_totals[pid]['combined_average'], reverse=True)
            for pos, pid in enumerate(ranked, start=1):
                combined_totals[pid]['class_combined_position'] = pos

            # Streams in this class
            stream_ids = set(p.stream_id for p in assigned_pupils if p.class_id == class_id and p.stream_id)
            for stream_id in stream_ids:
                stream_pids = [pid for pid in class_pupil_ids if any(p.id == pid and p.stream_id == stream_id for p in pupils_by_class.get(class_id, []))]
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
    # Count pupils across the whole class(es) (not only those assigned to this teacher)
    students_per_stream = {}
    students_per_class = {}
    for class_id in set(p.class_id for p in assigned_pupils):
        pupils_in_class_full = Pupil.query.filter_by(class_id=class_id).all()
        students_per_class[class_id] = len(pupils_in_class_full)
        for p in pupils_in_class_full:
            students_per_stream[p.stream_id] = students_per_stream.get(p.stream_id, 0) + 1

    # If this is an AJAX request, return only the table fragment for faster loads
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template(
            'teacher/_pupil_table_fragment.html',
            pupils=paged_assigned_pupils,
            combined_stats=combined_stats,
            students_per_stream=students_per_stream,
            students_per_class=students_per_class,
            report_map=report_map,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )

    return render_template(
        "teacher/manage_pupils_reports.html",
        teacher=teacher,
        pupils=paged_assigned_pupils,
        reports=reports,
        subjects=subjects,
        exams=exams,
        combined_stats=combined_stats,
        students_per_stream=students_per_stream,
        students_per_class=students_per_class,
        report_map=report_map,
        page=page,
        per_page=per_page,
        total=total_assigned,
        total_pages=total_pages
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
    # Build students per stream and class for this pupil's class
    pupils_in_class = Pupil.query.filter_by(class_id=pupil.class_id).all()
    students_per_stream = {}
    for p in pupils_in_class:
        students_per_stream[p.stream_id] = students_per_stream.get(p.stream_id, 0) + 1
    students_per_class = {pupil.class_id: len(pupils_in_class)}

    # Minimal class_stats: compute combined averages and positions for classmates grouped by term
    class_stats = {}
    subject_count = len(subjects) if subjects else 0
    exam_ids_all = exam_ids if exam_ids else []
    if exam_ids_all:
        all_exams = Exam.query.filter(Exam.id.in_(exam_ids_all)).all()
        term_groups = {}
        for ex in all_exams:
            term_groups.setdefault(ex.term, []).append(ex.id)

        for term, exam_ids_in_term in term_groups.items():
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

            combined_map = {}
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
                combined_map[p.id] = combined_avg

            if combined_map:
                class_average = round(sum(combined_map.values()) / len(combined_map), 2)
            else:
                class_average = None

            ranked = sorted(combined_map.items(), key=lambda kv: kv[1], reverse=True)
            class_positions = {pid: idx+1 for idx, (pid, _) in enumerate(ranked)}

            stream_pids = [p.id for p in pupils_in_class if p.stream_id == pupil.stream_id and p.id in combined_map]
            stream_ranked = sorted(stream_pids, key=lambda pid: combined_map.get(pid, 0), reverse=True)
            stream_positions = {pid: idx+1 for idx, pid in enumerate(stream_ranked)}

            class_stats[term] = {
                'class_average': class_average,
                'class_positions': class_positions,
                'stream_positions': stream_positions
            }

    return render_template(
        "teacher/reports.html",
        pupil=pupil,
        reports=reports,
        marks=marks,
        exams=exams,
        subjects=subjects,
        class_name=class_name,
        stream_name=stream_name,
        teacher=teacher,
        students_per_stream=students_per_stream,
        students_per_class=students_per_class,
        class_stats=class_stats
    )