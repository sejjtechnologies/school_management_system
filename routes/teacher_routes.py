from flask import Blueprint, render_template, session, flash, redirect, url_for, request, jsonify
from models.user_models import User, Role, db
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from models.register_pupils import Pupil
from models.marks_model import Subject, Exam, Mark, Report
from utils.grades import calculate_grade, calculate_general_remark
from models.attendance_model import Attendance
from models.attendance_log import AttendanceLog
from models.period_confirmation import PeriodConfirmation
import csv
import io
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import func
from datetime import datetime, timedelta
import json

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


@teacher_routes.route('/timetable')
def view_timetable():
    """Redirect a logged-in teacher to the timetable view for their assigned class & stream.
    If the teacher has multiple assignments, render a small chooser page.
    """
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not assignments:
        flash('You have no class/stream assignment. Contact admin.', 'warning')
        return redirect(url_for('teacher_routes.dashboard'))

    # If the teacher has a single assignment, redirect straight to the timetable manager page
    if len(assignments) == 1:
        a = assignments[0]
        # Redirect to the teacher read-only timetable view for the assigned class/stream
        return redirect(url_for('teacher_routes.view_timetable_view', class_id=a.class_id, stream_id=a.stream_id))

    # If multiple assignments, render a simple chooser so teacher picks which stream's timetable to view
    # Each choice links to the admin timetable manager with query params (view-only for teachers).
    choices = []
    for a in assignments:
        class_obj = Class.query.get(a.class_id)
        stream_obj = Stream.query.get(a.stream_id)
        choices.append({
            'assignment_id': a.id,
            'class_id': a.class_id,
            'stream_id': a.stream_id,
            'class_name': class_obj.name if class_obj else f'Class {a.class_id}',
            'stream_name': stream_obj.name if stream_obj else f'Stream {a.stream_id}'
        })

    return render_template('teacher/select_assignment.html', teacher=teacher, choices=choices)



@teacher_routes.route('/timetable/view/<int:class_id>/<int:stream_id>')
def view_timetable_view(class_id, stream_id):
    """Render a read-only timetable page for a teacher assigned to the provided class and stream.
    Only allowed if the logged-in teacher is assigned to that class+stream.
    """
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    # Verify assignment exists for this teacher
    assignment = TeacherAssignment.query.filter_by(teacher_id=teacher.id, class_id=class_id, stream_id=stream_id).first()
    if not assignment:
        flash('Access denied. You are not assigned to the selected class/stream.', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    class_obj = Class.query.get(class_id)
    stream_obj = Stream.query.get(stream_id)

    class_name = class_obj.name if class_obj else f'Class {class_id}'
    stream_name = stream_obj.name if stream_obj else f'Stream {stream_id}'

    return render_template('teacher/view_timetable.html', teacher=teacher, class_id=class_id, stream_id=stream_id, class_name=class_name, stream_name=stream_name)


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

        # Look up exam first (case-insensitive). If it exists and this pupil already has marks for it,
        # reject to prevent duplicate entry for the same pupil/year/term/exam.
        # Use a case-insensitive comparison to avoid accidental duplicates due to casing.
        exam = (
            Exam.query
            .filter(func.lower(Exam.name) == exam_name.lower(), Exam.term == term, Exam.year == year)
            .first()
        )
        if exam:
            # Robust duplicate check: look for any marks or reports for this pupil
            # associated with this exam id. If found, block the POST.
            existing_mark_check = Mark.query.filter_by(pupil_id=pupil_id, exam_id=exam.id).first()
            existing_report_check = Report.query.filter_by(pupil_id=pupil_id, exam_id=exam.id).first()
            if existing_mark_check or existing_report_check:
                message = (
                    "Marks for this pupil for the selected exam/term/year already exist. "
                    "Use edit if you want to update."
                )
                # DEBUG: write details to a debug log to help trace why duplicates are detected
                try:
                    with open('duplicate_debug.log', 'a') as dbg:
                        dbg.write(f"DUPLICATE BLOCK: pupil_id={pupil_id} exam_id={exam.id} ")
                        dbg.write(f"existing_mark={bool(existing_mark_check)} existing_report={bool(existing_report_check)}\n")
                except Exception:
                    pass
                # If request expects JSON (AJAX), return JSON error with 400.
                wants_json = (
                    request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                    'application/json' in request.headers.get('Accept', '')
                )
                if wants_json:
                    return jsonify({"success": False, "message": message}), 400
                # Otherwise render the template with an error message flashed/returned
                flash(message, 'danger')
                # Re-render the page with the form and error message
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

                return render_template(
                    "teacher/manage_pupils_marks.html",
                    pupils=pupils,
                    subjects=subjects,
                    streams=streams,
                    classes=classes,
                    years=years,
                    terms=terms,
                    exam_types=exam_types,
                    success_message=None,
                )
        else:
            # Create exam using the normalized name (spaces -> underscores preserved from exam_name)
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

        # ✅ AUTO-CREATE REPORT immediately after marks are saved
        # This ensures manage_reports always has fresh data when clicked
        marks = Mark.query.filter_by(pupil_id=pupil_id, exam_id=exam.id).all()
        if marks:
            total_score = sum(m.score for m in marks)
            average_score = total_score / len(marks) if marks else 0
            grade = calculate_grade(average_score)

            # Create or update report
            report = Report.query.filter_by(pupil_id=pupil_id, exam_id=exam.id).first()
            if not report:
                report = Report(
                    pupil_id=pupil_id,
                    exam_id=exam.id,
                    total_score=total_score,
                    average_score=average_score,
                    grade=grade,
                    remarks="Keep working hard!"
                )
                db.session.add(report)
            else:
                report.total_score = total_score
                report.average_score = average_score
                report.grade = grade

            db.session.commit()

        # ✅ Return JSON success message instead of redirecting
        return jsonify({
            "success": True,
            "message": "✅ Marks saved successfully!"
        })

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


@teacher_routes.route('/marks_status')
def marks_status():
    """Return JSON of saved exam names for a given pupil/year/term.
    Client uses this to disable already-saved exam options.
    """
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    try:
        pupil_id = int(request.args.get('pupil_id') or 0)
        year = int(request.args.get('year') or 0)
        term = int(request.args.get('term') or 0)
    except ValueError:
        return jsonify({'saved_exams': []})

    if not (pupil_id and year and term):
        return jsonify({'saved_exams': []})

    saved = []
    # Find exams for that year/term where marks or reports exist for this pupil
    exams = Exam.query.filter_by(year=year, term=term).all()
    for ex in exams:
        mark_exists = Mark.query.filter_by(pupil_id=pupil_id, exam_id=ex.id).first() is not None
        report_exists = Report.query.filter_by(pupil_id=pupil_id, exam_id=ex.id).first() is not None
        if mark_exists or report_exists:
            saved.append(ex.name)

    return jsonify({'saved_exams': saved})

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

    # ✅ Save combined stats back to all reports in this term
    for pid, stats in combined_totals.items():
        combined_grade = calculate_grade(stats['combined_average'])
        general_remark = calculate_general_remark(stats['combined_average'])
        class_pos = class_positions.get(pid)
        stream_pos = stream_positions.get(pid)

        # Update all reports for this pupil in this term
        term_reports = Report.query.filter(Report.pupil_id == pid, Report.exam_id.in_(exam_ids_in_term)).all()
        for rep in term_reports:
            rep.combined_total = stats['combined_total']
            rep.combined_average = stats['combined_average']
            rep.combined_grade = combined_grade
            rep.general_remark = general_remark
            rep.combined_position = class_pos

        stats['class_combined_position'] = class_pos
        stats['stream_combined_position'] = stream_pos
        stats['combined_grade'] = combined_grade
        stats['general_remark'] = general_remark

    db.session.commit()

    # Attach combined stats into a dict for the template
    combined_stats = {}
    for pid, stats in combined_totals.items():
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


# grading helpers imported from utils.grades


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


@teacher_routes.route('/attendance', methods=['GET', 'POST'])
def attendance_view():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    # GET: render new attendance marking page with all teacher assignments auto-loaded
    if request.method == 'GET':
        # Fetch teacher assignments with relationships eager-loaded
        assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()

        if not assignments:
            flash('You have no class assignments. Contact admin.', 'warning')
            return redirect(url_for('teacher_routes.dashboard'))

        # Get selected date or default to today
        selected_date_str = request.args.get('date')
        if selected_date_str:
            try:
                selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            except ValueError:
                selected_date = datetime.today().date()
        else:
            selected_date = datetime.today().date()

        # Load pupils across all assignments with real database data
        pupils_list = []
        seen = set()
        classes_seen = set()
        streams_data = {}
        attendance_map = {}  # Store existing attendance records

        for assignment in assignments:
            # Query pupils for this specific assignment
            pupils = Pupil.query.filter_by(
                class_id=assignment.class_id,
                stream_id=assignment.stream_id
            ).order_by(Pupil.last_name, Pupil.first_name).all()

            # Get class and stream info once
            class_obj = Class.query.get(assignment.class_id)
            stream_obj = Stream.query.get(assignment.stream_id)

            class_name = class_obj.name if class_obj else f"Class {assignment.class_id}"
            stream_name = stream_obj.name if stream_obj else f"Stream {assignment.stream_id}"

            # Store stream info
            if assignment.stream_id and assignment.stream_id not in streams_data:
                streams_data[assignment.stream_id] = stream_name

            # Add pupils to list (avoid duplicates)
            for pupil in pupils:
                if pupil.id not in seen:
                    seen.add(pupil.id)
                    pupils_list.append({
                        'id': pupil.id,
                        'admission_number': pupil.admission_number,
                        'first_name': pupil.first_name,
                        'last_name': pupil.last_name,
                        'full_name': f"{pupil.first_name} {pupil.last_name}",
                        'class_id': pupil.class_id,
                        'class_name': class_name,
                        'stream_id': pupil.stream_id,
                        'stream_name': stream_name
                    })

        # Load existing attendance for selected date but only for pupils in this teacher's assignments
        pupil_ids = [p['id'] for p in pupils_list]
        if pupil_ids:
            existing_attendance = Attendance.query.filter(Attendance.date == selected_date, Attendance.pupil_id.in_(pupil_ids)).all()
            for att in existing_attendance:
                attendance_map[att.pupil_id] = att.status

        # Build unique streams list
        all_streams = [
            {'id': stream_id, 'name': name}
            for stream_id, name in sorted(streams_data.items(), key=lambda x: x[1])
        ]

        # Determine primary class/stream from first assignment
        primary_class_name = ''
        primary_stream_name = ''
        if assignments:
            primary_class = Class.query.get(assignments[0].class_id)
            primary_stream = Stream.query.get(assignments[0].stream_id)
            primary_class_name = primary_class.name if primary_class else f"Class {assignments[0].class_id}"
            primary_stream_name = primary_stream.name if primary_stream else f"Stream {assignments[0].stream_id}"

        return render_template(
            'teacher/attendance_new.html',
            teacher=teacher,
            pupils=pupils_list,
            pupils_count=len(pupils_list),
            all_streams=all_streams,
            class_name=primary_class_name,
            stream_name=primary_stream_name,
            selected_date=selected_date.isoformat(),
            attendance_map=attendance_map
        )

    # POST: bulk upsert attendance (expects JSON payload with real data)
    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return (json.dumps({'error': f'Invalid JSON: {str(e)}'}), 400, {'Content-Type': 'application/json'})

    if not payload:
        return (json.dumps({'error': 'Empty payload'}), 400, {'Content-Type': 'application/json'})

    # Validate required fields
    class_id = payload.get('class_id')
    entries = payload.get('entries', [])
    attendance_date = payload.get('date')
    stream_id = payload.get('stream_id')

    if not class_id or not entries or not attendance_date:
        return (json.dumps({'error': 'Missing required fields: class_id, date, entries'}), 400, {'Content-Type': 'application/json'})

    # Validate teacher has permission for this class+stream
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    try:
        stream_id_int = int(stream_id) if stream_id is not None and stream_id != '' else None
    except (ValueError, TypeError):
        stream_id_int = None

    if stream_id_int is None:
        # If stream_id not provided, try to infer from first pupil entry later; but require assignment check will be done after inference
        pass
    else:
        if not any(a.class_id == int(class_id) and a.stream_id == stream_id_int for a in assignments):
            return (json.dumps({'error': 'Not authorized for this class/stream'}), 403, {'Content-Type': 'application/json'})

    try:
        class_id = int(class_id)
        attendance_date_obj = datetime.strptime(attendance_date, '%Y-%m-%d').date()
    except (ValueError, TypeError) as e:
        return (json.dumps({'error': f'Invalid date format: {str(e)}'}), 400, {'Content-Type': 'application/json'})

    # Check if attendance for this date has already been saved for this class+stream
    # Determine stream_id if not provided by looking up pupil records in entries
    if stream_id_int is None:
        # infer from first valid pupil in entries
        inferred_stream = None
        for entry in entries:
            pid = entry.get('pupil_id')
            try:
                p = Pupil.query.get(int(pid))
                if p:
                    inferred_stream = p.stream_id
                    break
            except Exception:
                continue
        stream_id_int = inferred_stream

    existing_count_query = Attendance.query.filter(Attendance.date == attendance_date_obj, Attendance.class_id == class_id)
    if stream_id_int is not None:
        existing_count_query = existing_count_query.filter(Attendance.stream_id == stream_id_int)

    existing_count = existing_count_query.count()

    # If attendance already exists for this date and class/stream, prevent re-saving
    if existing_count > 0:
        return (json.dumps({'error': 'Attendance for this date has already been saved. Cannot save twice.', 'already_saved': True}), 409, {'Content-Type': 'application/json'})

    # Prepare records for upsert with validation
    to_upsert = []
    logs_to_create = []
    invalid_pupils = []

    for entry in entries:
        try:
            pupil_id = int(entry.get('pupil_id'))
            status = (entry.get('status') or 'absent').lower().strip()

            # Validate status
            if status not in ('present', 'absent', 'late', 'leave'):
                status = 'absent'

            # Verify pupil exists and belongs to this class (and stream when available)
            if stream_id_int is not None:
                pupil = Pupil.query.filter_by(id=pupil_id, class_id=class_id, stream_id=stream_id_int).first()
            else:
                pupil = Pupil.query.filter_by(id=pupil_id, class_id=class_id).first()
            if not pupil:
                # record invalid pupil ids for reporting/debugging and skip
                try:
                    invalid_pupils.append(int(pupil_id))
                except Exception:
                    pass
                continue  # Skip invalid pupils

            # Since we already checked above, there should be no existing records
            # But create log for new records
            log_entry = AttendanceLog(
                pupil_id=pupil_id,
                date=attendance_date_obj,
                old_status=None,
                new_status=status,
                changed_by=teacher.id,
                reason=entry.get('reason')
            )
            logs_to_create.append(log_entry)

            to_upsert.append({
                'pupil_id': pupil_id,
                'class_id': class_id,
                'stream_id': pupil.stream_id,
                'date': attendance_date_obj,
                'status': status,
                'reason': entry.get('reason') or None,
                'recorded_by': teacher.id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        except (ValueError, TypeError, KeyError):
            continue  # Skip invalid entries

    if not to_upsert:
        return (json.dumps({'error': 'No valid attendance records to save'}), 400, {'Content-Type': 'application/json'})

    try:
        # Save audit logs first
        if logs_to_create:
            db.session.bulk_save_objects(logs_to_create)
            db.session.flush()

        # Upsert attendance records
        stmt = pg_insert(Attendance.__table__).values(to_upsert)
        upsert = stmt.on_conflict_do_update(
            index_elements=['pupil_id', 'date'],
            set_={
                'status': stmt.excluded.status,
                'reason': stmt.excluded.reason,
                'recorded_by': stmt.excluded.recorded_by,
                'updated_at': datetime.utcnow()
            }
        )
        db.session.execute(upsert)
        db.session.commit()

        msg = f'Successfully saved {len(to_upsert)} attendance records'
        if invalid_pupils:
            msg += f'. Skipped {len(invalid_pupils)} invalid pupil entries.'
        return (json.dumps({
            'ok': True,
            'message': msg,
            'count': len(to_upsert),
            'skipped_invalid_pupils': invalid_pupils
        }), 200, {'Content-Type': 'application/json'})

    except Exception as e:
        db.session.rollback()
        return (json.dumps({'error': f'Database error: {str(e)}'}), 500, {'Content-Type': 'application/json'})


@teacher_routes.route('/attendance/export')
def attendance_export():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    class_id = request.args.get('class_id', type=int)
    start_date_str = request.args.get('start')
    period = request.args.get('period', 'week')
    days = request.args.get('days', type=int, default=6)

    # Validate parameters
    if not class_id:
        flash('Class ID is required', 'danger')
        return redirect(url_for('teacher_routes.attendance_summary'))

    # Permission check
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not any(a.class_id == class_id for a in assignments):
        flash('Not authorized to export attendance for this class', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    # Parse start date
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            today = datetime.today().date()
            start_date = today - timedelta(days=today.weekday())
    except ValueError:
        flash('Invalid start date format', 'danger')
        return redirect(url_for('teacher_routes.attendance_summary'))

    # Calculate end date based on period
    if period == 'week':
        if days not in (5, 6):
            days = 6
        end_date = start_date + timedelta(days=days - 1)
    elif period == 'month':
        # Last day of month
        next_month = start_date.replace(day=1) + timedelta(days=32)
        end_date = next_month.replace(day=1) - timedelta(days=1)
    elif period == 'term':
        days = days if days > 0 and days <= 365 else 105
        end_date = start_date + timedelta(days=days - 1)
    else:
        end_date = start_date + timedelta(days=29)

    # Query attendance data from database
    attendance_records = Attendance.query.join(Pupil).filter(
        Pupil.class_id == class_id,
        Attendance.date.between(start_date, end_date)
    ).order_by(Pupil.last_name, Pupil.first_name, Attendance.date).all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Admission Number',
        'Pupil Name',
        'Date',
        'Status',
        'Reason',
        'Recorded By',
        'Last Updated'
    ])

    for record in attendance_records:
        pupil = Pupil.query.get(record.pupil_id)
        recorded_by_user = User.query.get(record.recorded_by)

        writer.writerow([
            pupil.admission_number if pupil else '',
            f"{pupil.first_name} {pupil.last_name}" if pupil else '',
            record.date.isoformat(),
            record.status,
            record.reason or '',
            recorded_by_user.email if recorded_by_user else '',
            record.updated_at.strftime('%Y-%m-%d %H:%M:%S') if record.updated_at else ''
        ])

    # Prepare response
    csv_content = output.getvalue()
    class_obj = Class.query.get(class_id)
    class_name = class_obj.name if class_obj else f"Class_{class_id}"
    filename = f"attendance_{class_name}_{start_date.isoformat()}_to_{end_date.isoformat()}.csv"

    return (
        csv_content,
        200,
        {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@teacher_routes.route('/attendance/summary')
def attendance_summary():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    class_id = request.args.get('class_id', type=int)
    start_date_str = request.args.get('start')
    period = request.args.get('period', 'week')
    days = request.args.get('days', type=int, default=6)

    # Parse start date
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            today = datetime.today().date()
            start_date = today - timedelta(days=today.weekday())
    except ValueError:
        flash('Invalid date format', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    # Calculate end date based on period
    if period == 'week':
        if days not in (5, 6):
            days = 6
        end_date = start_date + timedelta(days=days - 1)
    elif period == 'month':
        # Last day of month
        next_month = start_date.replace(day=1) + timedelta(days=32)
        end_date = next_month.replace(day=1) - timedelta(days=1)
    elif period == 'term':
        days = days if days > 0 and days <= 365 else 105
        end_date = start_date + timedelta(days=days - 1)
    else:
        end_date = start_date + timedelta(days=29)

    # Permission check
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if class_id and not any(a.class_id == class_id for a in assignments):
        flash('Not authorized for this class', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    # Set default class_id from first assignment if not provided
    if not class_id and assignments:
        class_id = assignments[0].class_id

    # Get assigned stream for this teacher/class combination
    assigned_stream_id = None
    assigned_stream_name = None

    for assignment in assignments:
        if assignment.class_id == class_id:
            assigned_stream_id = assignment.stream_id
            break

    if not assigned_stream_id and assignments:
        assigned_stream_id = assignments[0].stream_id

    if assigned_stream_id:
        stream_obj = Stream.query.get(assigned_stream_id)
        assigned_stream_name = stream_obj.name if stream_obj else None

    # Query pupils for this class and stream
    if assigned_stream_id:
        pupils = Pupil.query.filter_by(
            class_id=class_id,
            stream_id=assigned_stream_id
        ).order_by(Pupil.last_name, Pupil.first_name).all()
    else:
        pupils = Pupil.query.filter_by(class_id=class_id).order_by(Pupil.last_name, Pupil.first_name).all()

    # Calculate total possible days in period
    total_days_in_period = (end_date - start_date).days + 1

    # Build attendance summary for each pupil
    summary_data = []
    for pupil in pupils:
        # Query attendance records for this pupil in date range
        attendance_records = Attendance.query.filter_by(pupil_id=pupil.id).filter(
            Attendance.date.between(start_date, end_date)
        ).all()

        # Count by status
        status_counts = {
            'present': 0,
            'absent': 0,
            'late': 0,
            'leave': 0
        }
        attendance_by_date = {}

        for record in attendance_records:
            if record.status in status_counts:
                status_counts[record.status] += 1
            attendance_by_date[record.date.isoformat()] = record.status

        # For term view: calculate percentage based on total days in period
        # For other views: calculate based on recorded days
        if period == 'term':
            total_days_for_calc = total_days_in_period
        else:
            total_days_for_calc = len(attendance_records)

        # Calculate attendance percentage
        attendance_percentage = round(
            (status_counts['present'] + status_counts['late']) / total_days_for_calc * 100, 1
        ) if total_days_for_calc > 0 else 0

        summary_data.append({
            'pupil_id': pupil.id,
            'admission_number': pupil.admission_number,
            'name': f"{pupil.first_name} {pupil.last_name}",
            'first_name': pupil.first_name,
            'last_name': pupil.last_name,
            'counts': status_counts,
            'attendance_by_date': attendance_by_date,
            'attendance_percentage': attendance_percentage,
            'total_days': len(attendance_records),
            'stream_id': pupil.stream_id,
            'stream_name': (Stream.query.get(pupil.stream_id).name if pupil.stream_id else None)
        })

    # Build date range for display (only for day-by-day views)
    date_range = []
    if period in ('week', 'month'):
        current = start_date
        while current <= end_date:
            date_range.append({
                'iso': current.isoformat(),
                'short': current.strftime('%a'),
                'full': current.strftime('%m/%d'),
                'numeric': current.strftime('%d')
            })
            current += timedelta(days=1)

    # Get class info
    class_obj = Class.query.get(class_id)
    class_name = class_obj.name if class_obj else f"Class {class_id}"

    # Check if period is confirmed
    period_confirmed = PeriodConfirmation.query.filter_by(
        class_id=class_id,
        start_date=start_date,
        period_type=period,
        days=days
    ).first() is not None

    # Prepare summary object
    summary = {
        'start': start_date.isoformat(),
        'end': end_date.isoformat(),
        'start_formatted': start_date.strftime('%B %d, %Y'),
        'end_formatted': end_date.strftime('%B %d, %Y'),
        'data': summary_data,
        'total_days': total_days_in_period,
        'period': period,
        'period_confirmed': period_confirmed,
        'pupils_count': len(pupils)
    }

    return render_template(
        'teacher/attendance_summary.html',
        teacher=teacher,
        summary=summary,
        dates=date_range,
        class_name=class_name,
        stream_name=assigned_stream_name,
        start_date=start_date.isoformat(),
        period=period,
        days=days
    )


@teacher_routes.route('/attendance/confirm', methods=['POST'])
def attendance_confirm():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    try:
        payload = request.get_json(force=True)
    except Exception as e:
        return (
            json.dumps({'error': f'Invalid JSON: {str(e)}'}),
            400,
            {'Content-Type': 'application/json'}
        )

    if not payload:
        return (
            json.dumps({'error': 'Empty payload'}),
            400,
            {'Content-Type': 'application/json'}
        )

    # Extract parameters
    class_id = payload.get('class_id')
    start_date_str = payload.get('start')
    period = payload.get('period', 'week')
    days = int(payload.get('days', 6))
    confirm = bool(payload.get('confirm', True))

    # Validate required fields
    if not class_id or not start_date_str:
        return (
            json.dumps({'error': 'Missing required fields: class_id, start'}),
            400,
            {'Content-Type': 'application/json'}
        )

    # Permission check
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if not any(a.class_id == int(class_id) for a in assignments):
        return (
            json.dumps({'error': 'Not authorized for this class'}),
            403,
            {'Content-Type': 'application/json'}
        )

    # Parse dates
    try:
        class_id = int(class_id)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError) as e:
        return (
            json.dumps({'error': f'Invalid date format: {str(e)}'}),
            400,
            {'Content-Type': 'application/json'}
        )

    # Calculate end date
    if period == 'week':
        if days not in (5, 6):
            days = 6
        end_date = start_date + timedelta(days=days - 1)
    elif period == 'month':
        next_month = start_date.replace(day=1) + timedelta(days=32)
        end_date = next_month.replace(day=1) - timedelta(days=1)
    elif period == 'term':
        days = days if days > 0 and days <= 365 else 105
        end_date = start_date + timedelta(days=days - 1)
    else:
        end_date = start_date + timedelta(days=29)

    try:
        if confirm:
            # Check if already confirmed
            existing = PeriodConfirmation.query.filter_by(
                class_id=class_id,
                start_date=start_date,
                period_type=period,
                days=days
            ).first()

            if existing:
                return (
                    json.dumps({
                        'ok': True,
                        'confirmed': True,
                        'message': 'Period already confirmed'
                    }),
                    200,
                    {'Content-Type': 'application/json'}
                )

            # Create new confirmation record
            confirmation = PeriodConfirmation(
                class_id=class_id,
                start_date=start_date,
                end_date=end_date,
                period_type=period,
                days=days,
                confirmed_by=teacher.id,
                confirmed_at=datetime.utcnow()
            )
            db.session.add(confirmation)
            db.session.commit()

            return (
                json.dumps({
                    'ok': True,
                    'confirmed': True,
                    'message': f'Attendance period confirmed: {start_date.isoformat()} to {end_date.isoformat()}',
                    'confirmation_id': confirmation.id
                }),
                200,
                {'Content-Type': 'application/json'}
            )
        else:
            # Remove confirmation if it exists
            existing = PeriodConfirmation.query.filter_by(
                class_id=class_id,
                start_date=start_date,
                period_type=period,
                days=days
            ).first()

            if existing:
                db.session.delete(existing)
                db.session.commit()

            return (
                json.dumps({
                    'ok': True,
                    'confirmed': False,
                    'message': 'Period confirmation removed'
                }),
                200,
                {'Content-Type': 'application/json'}
            )

    except Exception as e:
        db.session.rollback()
        return (
            json.dumps({'error': f'Database error: {str(e)}'}),
            500,
            {'Content-Type': 'application/json'}
        )