"""Teacher reports blueprint: list/manage pupils reports, prepare and print selected exams.

This module provides the following endpoints:
- /teacher/manage_pupils_reports (GET): listing with filters and pagination
- /teacher/pupil/<pupil_id> (GET): view single pupil report
- /teacher/pupil/<pupil_id>/prepare_print (GET): choose exams to print
- /teacher/pupil/<pupil_id>/print (GET): render print-optimized HTML

The implementation favors clarity and correctness and avoids N+1 queries by batching
important database fetches.
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash, request
import datetime
from sqlalchemy import or_, and_

from models.user_models import db
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from models.marks_model import Subject, Exam, Mark, Report

from routes.teacher_routes import _require_teacher
from utils.grades import calculate_grade, calculate_general_remark

# Blueprint
teacher_manage_reports = Blueprint("teacher_manage_reports", __name__, url_prefix="/teacher")


# grading helpers are imported from utils.grades


@teacher_manage_reports.route('/manage_pupils_reports')
def manage_pupils_reports():
    """List pupils assigned to the logged-in teacher, allow filtering by year/term/exam-type,
    compute per-exam reports (upsert) and combined-term aggregates (mid=40%/end=60% heuristics).
    Returns an AJAX fragment when requested.
    """
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    # fetch teacher assignments and assigned pupils
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    assigned_pupils = []
    if assignments:
        filters = [and_(Pupil.class_id == a.class_id, Pupil.stream_id == a.stream_id) for a in assignments]
        if filters:
            assigned_pupils = Pupil.query.filter(or_(*filters)).all()

    # pagination
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    try:
        per_page = int(request.args.get('per_page', 50))
    except ValueError:
        per_page = 50

    if not assigned_pupils:
        return render_template(
            "teacher/manage_pupils_reports.html",
            teacher=teacher,
            pupils=[],
            reports=[],
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
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    start = (page - 1) * per_page
    end = start + per_page
    paged_assigned_pupils = assigned_pupils[start:end]

    assigned_ids = [p.id for p in assigned_pupils]

    # Prefetch class/stream maps
    class_ids = list(set(p.class_id for p in assigned_pupils if p.class_id))
    stream_ids = list(set(p.stream_id for p in assigned_pupils if p.stream_id))
    class_map = {c.id: c for c in Class.query.filter(Class.id.in_(class_ids)).all()} if class_ids else {}
    stream_map = {s.id: s for s in Stream.query.filter(Stream.id.in_(stream_ids)).all()} if stream_ids else {}

    # parse filters
    try:
        selected_year = int(request.args.get('year')) if request.args.get('year') else datetime.date.today().year
    except ValueError:
        selected_year = datetime.date.today().year
    term_param = request.args.get('term')
    try:
        selected_term = int(term_param) if term_param and term_param.lower() != 'all' else None
    except ValueError:
        selected_term = None
    types_param = (request.args.get('types') or 'both').lower()

    exams_q = Exam.query.filter(Exam.year == selected_year)
    if selected_term is not None:
        exams_q = exams_q.filter(Exam.term == selected_term)
    if types_param != 'both':
        if types_param == 'mid':
            exams_q = exams_q.filter(Exam.name.ilike('%mid%'))
        elif types_param == 'end':
            exams_q = exams_q.filter(Exam.name.ilike('%end%'))

    selected_exams = exams_q.all()
    selected_exam_ids = [e.id for e in selected_exams]

    # ✅ ONLY FETCH existing reports - don't create/update them here
    # Reports should be created when marks are entered, not here
    reports = []
    if selected_exam_ids:
        reports = Report.query.filter(Report.pupil_id.in_(assigned_ids), Report.exam_id.in_(selected_exam_ids)).all()

    # Build report map for template
    report_map = {(r.pupil_id, r.exam_id): r for r in reports}

    # Attach class/stream names to pupils
    for pupil in assigned_pupils:
        class_obj = class_map.get(pupil.class_id)
        stream_obj = stream_map.get(pupil.stream_id)
        pupil.class_name = class_obj.name if class_obj else (f"Class {pupil.class_id}" if pupil.class_id else 'N/A')
        pupil.stream_name = stream_obj.name if stream_obj else (f"Stream {pupil.stream_id}" if pupil.stream_id else 'N/A')

    # Prepare subject count and pupils_by_class map
    subjects = Subject.query.all()
    subject_count = len(subjects) if subjects else 0
    pupils_by_class = {}
    classes_to_check = set(p.class_id for p in assigned_pupils if p.class_id)
    if classes_to_check:
        all_class_pupils = Pupil.query.filter(Pupil.class_id.in_(classes_to_check)).all()
        for cid in classes_to_check:
            pupils_by_class[cid] = [p for p in all_class_pupils if p.class_id == cid]

    # ✅ ONLY FETCH existing reports from database - no calculations
    # Combined stats are pre-calculated when reports are created
    combined_stats = {}

    # Prepare template lists and counts
    subjects = Subject.query.all()
    exams = selected_exams
    students_per_stream = {}
    students_per_class = {}
    for cid, pupils_in_class_full in pupils_by_class.items():
        students_per_class[cid] = len(pupils_in_class_full)
        for p in pupils_in_class_full:
            students_per_stream[p.stream_id] = students_per_stream.get(p.stream_id, 0) + 1

    # years list
    current_year = datetime.date.today().year
    years = list(range(current_year - 2, current_year + 1))
    if selected_year not in years:
        years.append(selected_year)
        years = sorted(years)

    # Build rep fallback map for template
    reports_by_pupil = {}
    for r in reports:
        reports_by_pupil.setdefault(r.pupil_id, []).append(r)
    report_map = {pid: reps[0] for pid, reps in reports_by_pupil.items() if reps}

    # AJAX fragment support
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('teacher/_pupil_table_fragment.html', pupils=paged_assigned_pupils, combined_stats=combined_stats, students_per_stream=students_per_stream, students_per_class=students_per_class, report_map=report_map, page=page, per_page=per_page, total_pages=total_pages, selected_year=selected_year, selected_term=selected_term, selected_types=types_param)

    return render_template('teacher/manage_pupils_reports.html', teacher=teacher, pupils=paged_assigned_pupils, reports=reports, subjects=subjects, exams=exams, combined_stats=combined_stats, students_per_stream=students_per_stream, students_per_class=students_per_class, report_map=report_map, page=page, per_page=per_page, total=total_assigned, total_pages=total_pages, selected_year=selected_year, selected_term=selected_term, selected_types=types_param, years=years)


@teacher_manage_reports.route("/pupil/<int:pupil_id>", methods=["GET"])
def view_pupil_report(pupil_id):
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    pupil = Pupil.query.get_or_404(pupil_id)
    reports = Report.query.filter_by(pupil_id=pupil.id).all()
    marks = Mark.query.filter_by(pupil_id=pupil.id).all()
    exam_ids = [r.exam_id for r in reports]
    exams = Exam.query.filter(Exam.id.in_(exam_ids)).all() if exam_ids else []
    subjects = Subject.query.all()

    # Fetch proper class and stream names
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


@teacher_manage_reports.route('/pupil/<int:pupil_id>/prepare_print', methods=['GET'])
def prepare_print(pupil_id):
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    # parse filters from querystring
    try:
        selected_year = int(request.args.get('year')) if request.args.get('year') else None
    except ValueError:
        selected_year = None
    term_param = request.args.get('term')
    try:
        selected_term = int(term_param) if term_param and term_param.lower() != 'all' else None
    except ValueError:
        selected_term = None
    types_param = (request.args.get('types') or 'both').lower()

    pupil = Pupil.query.get_or_404(pupil_id)

    # Build exam query limited by filters
    # Note: For prepare_print, we show ALL exams by default (no term filter)
    # unless explicitly filtered. Users can select term via quick buttons.
    exams_q = Exam.query
    if selected_year:
        exams_q = exams_q.filter(Exam.year == selected_year)
    # Don't filter by term by default on prepare_print - show all terms
    # if selected_term is not None:
    #     exams_q = exams_q.filter(Exam.term == selected_term)
    if types_param != 'both' and types_param != 'all':
        if types_param == 'mid':
            exams_q = exams_q.filter(Exam.name.ilike('%mid%'))
        elif types_param == 'end':
            exams_q = exams_q.filter(Exam.name.ilike('%end%'))

    exams_filtered = exams_q.all()
    # Filter to only generic Midterm and End Term exams (not subject-specific)
    exams_filtered = [e for e in exams_filtered if e.name in ['Midterm', 'End Term', 'End_term', 'End_Term']]
    exam_ids = [e.id for e in exams_filtered]

    # determine which of these exams have reports/marks for this pupil
    available_exams = []
    if exam_ids:
        reps = Report.query.filter(Report.pupil_id == pupil.id, Report.exam_id.in_(exam_ids)).all()
        rep_exam_ids = set(r.exam_id for r in reps)
        # also consider marks if reports don't exist
        marks_exist = {m.exam_id for m in Mark.query.filter(Mark.pupil_id == pupil.id, Mark.exam_id.in_(exam_ids)).all()}
        have_ids = rep_exam_ids.union(marks_exist)
        available_exams = [e for e in exams_filtered if e.id in have_ids]
        # Sort by term and then by name (Midterm before End Term)
        available_exams = sorted(available_exams, key=lambda e: (e.term, 'Midterm' not in e.name))

    return render_template('teacher/prepare_print.html', pupil=pupil, available_exams=available_exams, selected_year=selected_year, selected_term=selected_term, selected_types=types_param)


@teacher_manage_reports.route('/pupil/<int:pupil_id>/print', methods=['GET'])
def print_selected(pupil_id):
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp
    import datetime as _dt
    start_time = _dt.datetime.now()
    print(f"[PRINT_SELECTED] start {start_time.isoformat()}")

    pupil = Pupil.query.get_or_404(pupil_id)
    exam_ids_param = request.args.get('exam_ids') or ''
    try:
        exam_ids = [int(x) for x in exam_ids_param.split(',') if x.strip()]
    except ValueError:
        exam_ids = []

    if not exam_ids:
        flash('No exams selected for printing.', 'warning')
        return redirect(url_for('teacher_manage_reports.prepare_print', pupil_id=pupil.id))

    # fetch exams, reports and marks for those exam ids
    exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()
    # Sort exams by term and then by name (Midterm before End Term)
    exams = sorted(exams, key=lambda e: (e.term, 'Midterm' not in e.name))
    print(f"[PRINT_SELECTED] fetched exams ({len(exams)}) at " + _dt.datetime.now().isoformat())
    reports = Report.query.filter(Report.pupil_id == pupil.id, Report.exam_id.in_(exam_ids)).all()
    print(f"[PRINT_SELECTED] fetched pupil reports ({len(reports)}) at " + _dt.datetime.now().isoformat())
    marks = Mark.query.filter(Mark.pupil_id == pupil.id, Mark.exam_id.in_(exam_ids)).all()
    print(f"[PRINT_SELECTED] fetched pupil marks ({len(marks)}) at " + _dt.datetime.now().isoformat())
    subjects = Subject.query.all()
    print(f"[PRINT_SELECTED] fetched subjects ({len(subjects)}) at " + _dt.datetime.now().isoformat())

    # Build marks map: exam_id -> list of marks
    marks_by_exam = {}
    for m in marks:
        marks_by_exam.setdefault(m.exam_id, []).append(m)

    # optionally compute combined stats across selected exams using the same heuristics
    weights_template = {}
    for ex in exams:
        name = (ex.name or '').lower()
        if 'mid' in name:
            weights_template[ex.id] = 0.4
        elif 'end' in name or 'end term' in name:
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

    # compute combined if more than one exam
    combined = None
    if len(exams) > 1:
        subject_count = len(subjects) if subjects else 1
        weighted_total = 0.0
        for ex in exams:
            rep = next((r for r in reports if r.exam_id == ex.id), None)
            if rep:
                weighted_total += (rep.total_score or 0) * weights_template.get(ex.id, 0)
            else:
                # fallback: sum marks for the exam
                mlist = marks_by_exam.get(ex.id, [])
                total = sum(m.score for m in mlist) if mlist else 0
                weighted_total += total * weights_template.get(ex.id, 0)
        combined_avg = round(weighted_total / (subject_count or 1))
        combined = {'combined_total': round(weighted_total,2), 'combined_average': combined_avg, 'combined_grade': calculate_grade(combined_avg), 'general_remark': calculate_general_remark(combined_avg)}

    # compute stream positions for each exam and class combined position (if multiple exams)
    exam_stats = {}  # exam_id -> {stream_position, stream_total}

    # pupils in same class+stream (stream positions)
    stream_pupils = Pupil.query.filter_by(class_id=pupil.class_id, stream_id=pupil.stream_id).all()
    stream_pupil_ids = [p.id for p in stream_pupils]
    stream_total = len(stream_pupil_ids)

    # pupils in same class (class combined positions)
    class_pupils = Pupil.query.filter_by(class_id=pupil.class_id).all()
    class_pupil_ids = [p.id for p in class_pupils]
    class_total = len(class_pupil_ids)

    # To avoid N+1 queries, fetch all reports and marks for pupils in this class/stream
    relevant_pupil_ids = set(stream_pupil_ids) | set(class_pupil_ids)
    reports_all = Report.query.filter(Report.pupil_id.in_(relevant_pupil_ids), Report.exam_id.in_(exam_ids)).all() if exam_ids else []
    print(f"[PRINT_SELECTED] fetched reports_all ({len(reports_all)}) for relevant pupils at " + _dt.datetime.now().isoformat())
    marks_all = Mark.query.filter(Mark.pupil_id.in_(relevant_pupil_ids), Mark.exam_id.in_(exam_ids)).all() if exam_ids else []
    print(f"[PRINT_SELECTED] fetched marks_all ({len(marks_all)}) for relevant pupils at " + _dt.datetime.now().isoformat())

    # build maps for fast lookup
    reports_map = {(r.pupil_id, r.exam_id): r for r in reports_all}
    marks_map = {}
    for m in marks_all:
        marks_map.setdefault((m.pupil_id, m.exam_id), []).append(m)

    for ex in exams:
        # build list of (pupil_id, avg) for pupils in same stream using cached maps
        vals = []
        for pid in stream_pupil_ids:
            rep = reports_map.get((pid, ex.id))
            if rep and rep.average_score is not None:
                avg = rep.average_score
            else:
                mlist = marks_map.get((pid, ex.id), [])
                if mlist:
                    avg = sum(m.score for m in mlist) / len(mlist)
                else:
                    avg = None
            if avg is not None:
                vals.append((pid, avg))

        # rank
        ranked = sorted(vals, key=lambda kv: kv[1], reverse=True)
        pos = None
        for idx, (pid, _) in enumerate(ranked, start=1):
            if pid == pupil.id:
                pos = idx
                break
        exam_stats[ex.id] = {'stream_position': pos, 'stream_total': stream_total}

    # compute combined class ranking if combined was calculated
    class_position = None
    if combined:
        # compute combined for all pupils in class using cached reports/marks maps
        class_vals = []
        for pid in class_pupil_ids:
            weighted_total_p = 0.0
            has_any = False
            for ex in exams:
                rep = reports_map.get((pid, ex.id))
                if rep:
                    weighted_total_p += (rep.total_score or 0) * weights_template.get(ex.id, 0)
                    has_any = True
                else:
                    mlist = marks_map.get((pid, ex.id), [])
                    if mlist:
                        total = sum(m.score for m in mlist)
                        weighted_total_p += total * weights_template.get(ex.id, 0)
                        has_any = True
            if has_any:
                avg_p = round((weighted_total_p / (subject_count or 1)), 2)
                class_vals.append((pid, avg_p))

        ranked_class = sorted(class_vals, key=lambda kv: kv[1], reverse=True)
        for idx, (pid, _) in enumerate(ranked_class, start=1):
            if pid == pupil.id:
                class_position = idx
                break
    print(f"[PRINT_SELECTED] finished calculations at " + _dt.datetime.now().isoformat())

    # find class teacher for this class/stream
    class_teacher = None
    ta = TeacherAssignment.query.filter_by(class_id=pupil.class_id, stream_id=pupil.stream_id).first()
    if ta and hasattr(ta, 'teacher'):
        class_teacher = ta.teacher

    # attach class/stream names for template
    class_obj = Class.query.get(pupil.class_id) if pupil.class_id else None
    stream_obj = Stream.query.get(pupil.stream_id) if pupil.stream_id else None
    pupil.class_name = class_obj.name if class_obj else (f"Class {pupil.class_id}" if pupil.class_id else 'N/A')
    pupil.stream_name = stream_obj.name if stream_obj else (f"Stream {pupil.stream_id}" if pupil.stream_id else 'N/A')

    return render_template('teacher/print_selected.html', pupil=pupil, exams=exams, reports=reports, marks_by_exam=marks_by_exam, subjects=subjects, combined=combined, exam_stats=exam_stats, class_position=class_position, class_total=class_total, class_teacher=class_teacher)