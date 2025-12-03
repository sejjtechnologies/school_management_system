from flask import Blueprint, render_template, session, flash, redirect, url_for, request
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
from datetime import datetime, timedelta
import json
import json as json_lib

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
        # fetch teacher assignments
        assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
        
        if not assignments:
            flash('You have no class assignments. Contact admin.', 'warning')
            return redirect(url_for('teacher_routes.dashboard'))
        
        # Load pupils across all assignments
        pupils_list = []
        for a in assignments:
            ps = Pupil.query.filter_by(class_id=a.class_id, stream_id=a.stream_id).order_by(Pupil.last_name).all()
            pupils_list.extend([{
                'id': p.id,
                'first_name': p.first_name,
                'last_name': p.last_name,
                'class_id': p.class_id,
                'stream_id': p.stream_id
            } for p in ps])
        
        # Get all streams teacher teaches
        all_streams = []
        for a in assignments:
            s = Stream.query.get(a.stream_id)
            if s and s.id not in [st['id'] for st in all_streams]:
                all_streams.append({'id': s.id, 'name': s.name})
        
        pupils_json = json_lib.dumps(pupils_list)
        all_streams_json = json_lib.dumps(all_streams)
        
        return render_template('teacher/attendance_new.html', teacher=teacher, pupils_json=pupils_json, all_streams_json=all_streams_json)

    # POST: bulk upsert attendance (expects JSON payload)
    try:
        payload = request.get_json(force=True)
    except Exception:
        payload = None

    if not payload:
        flash('Invalid attendance payload', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    class_id = int(payload.get('class_id')) if payload.get('class_id') else None
    entries = payload.get('entries', [])
    confirm_period = bool(payload.get('confirm_period', False))

    # permission check
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if class_id and not any(a.class_id == class_id for a in assignments):
        return (json.dumps({'error':'not allowed'}), 403, {'Content-Type':'application/json'})

    # Prepare list of dicts for insert
    to_insert = []
    for e in entries:
        try:
            pid = int(e.get('pupil_id'))
            dt_raw = e.get('date')
            # expect 'YYYY-MM-DD' from frontend; normalize to date object
            dt_obj = datetime.strptime(dt_raw, '%Y-%m-%d').date()
            status = (e.get('status') or 'absent').lower()
            if status not in ('present', 'absent', 'late', 'leave'):
                status = 'absent'
        except Exception:
            continue
        entry_class = int(e.get('class_id')) if e.get('class_id') else class_id
        entry_stream = int(e.get('stream_id')) if e.get('stream_id') else None
        to_insert.append({
            'pupil_id': pid,
            'class_id': entry_class,
            'stream_id': entry_stream,
            'date': dt_obj,
            'status': status,
            'reason': e.get('reason') or None,
            'recorded_by': teacher.id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })

    # Audit: fetch existing attendance for these pupil/date keys and create logs for changes
    keys = [(item['pupil_id'], item['date']) for item in to_insert]
    existing = {}
    if keys:
        pupil_ids = list({k[0] for k in keys})
        dates = [k[1] for k in keys]
        rows = Attendance.query.filter(Attendance.pupil_id.in_(pupil_ids), Attendance.date.in_(dates)).all()
        for r in rows:
            existing[(r.pupil_id, r.date.isoformat())] = r

    logs = []
    for item in to_insert:
        key = (item['pupil_id'], item['date'].isoformat())
        ex = existing.get(key)
        old_status = ex.status if ex else None
        new_status = item['status']
        if old_status != new_status:
            logs.append(AttendanceLog(
                attendance_id=ex.id if ex else None,
                pupil_id=item['pupil_id'],
                date=item['date'],
                old_status=old_status,
                new_status=new_status,
                changed_by=teacher.id,
                reason=item.get('reason')
            ))

    if logs:
        db.session.bulk_save_objects(logs)
        db.session.flush()

    if to_insert:
        stmt = pg_insert(Attendance.__table__).values(to_insert)
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


    return (json.dumps({'ok':True}), 200, {'Content-Type':'application/json'})


@teacher_routes.route('/attendance/export')
def attendance_export():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    class_id = request.args.get('class_id', type=int)
    start = request.args.get('start')
    period = request.args.get('period', 'week')  # 'week' or 'month'

    # basic permission check
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if class_id and not any(a.class_id == class_id for a in assignments):
        flash('Not allowed', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    try:
        if start:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
        else:
            today = datetime.today().date()
            start_date = today - timedelta(days=today.weekday())
    except Exception:
        flash('Invalid date', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    if period == 'week':
        # respect days parameter if provided (default Mon-Sat -> 6 days)
        days = request.args.get('days', default=6, type=int)
        if days not in (5, 6):
            days = 6
        end_date = start_date + timedelta(days=days-1)
    else:
        # month: use first day of month
        end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # fetch attendance
    rows = Attendance.query.join(Pupil).filter(
        Pupil.class_id == class_id,
        Attendance.date.between(start_date, end_date)
    ).order_by(Pupil.last_name, Attendance.date).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Pupil ID', 'First Name', 'Last Name', 'Date', 'Status', 'Reason'])
    for r in rows:
        pupil = Pupil.query.get(r.pupil_id)
        writer.writerow([r.pupil_id, pupil.first_name if pupil else '', pupil.last_name if pupil else '', r.date.isoformat(), r.status, r.reason or ''])

    resp = output.getvalue()
    filename = f"attendance_{class_id}_{start_date.isoformat()}_{period}.csv"
    return (resp, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename={filename}'
    })


@teacher_routes.route('/attendance/summary')
def attendance_summary():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    class_id = request.args.get('class_id', type=int)
    start = request.args.get('start')
    period = request.args.get('period', 'week')

    try:
        if start:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
        else:
            today = datetime.today().date()
            start_date = today - timedelta(days=today.weekday())
    except Exception:
        flash('Invalid date', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    if period == 'week':
        days = request.args.get('days', default=6, type=int)
        if days not in (5, 6):
            days = 6
        end_date = start_date + timedelta(days=days-1)
    else:
        end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # permission
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if class_id and not any(a.class_id == class_id for a in assignments):
        flash('Not allowed', 'danger')
        return redirect(url_for('teacher_routes.dashboard'))

    # if no class_id, default to first assignment's class
    if not class_id and assignments:
        class_id = assignments[0].class_id

    pupils = Pupil.query.filter_by(class_id=class_id).order_by(Pupil.last_name).all()
    pupil_ids = [p.id for p in pupils]

    # Build date range with formatted labels
    date_range = []
    current = start_date
    while current <= end_date:
        date_range.append({
            'iso': current.isoformat(),
            'short': current.strftime('%a'),  # Mon, Tue, etc.
            'full': current.strftime('%m/%d')  # 01/20, etc.
        })
        current += timedelta(days=1)

    # aggregate attendance data
    summary_data = []
    for p in pupils:
        counts = {
            'present': 0,
            'absent': 0,
            'late': 0,
            'leave': 0
        }
        attendance_by_date = {}
        rows = Attendance.query.filter_by(pupil_id=p.id).filter(Attendance.date.between(start_date, end_date)).all()
        for r in rows:
            if r.status in counts:
                counts[r.status] += 1
            attendance_by_date[r.date.isoformat()] = r.status
        summary_data.append({
            'pupil_id': p.id,
            'name': f"{p.first_name} {p.last_name}",
            'counts': counts,
            'attendance_by_date': attendance_by_date
        })

    summary = {
        'start': start_date.isoformat(),
        'end': end_date.isoformat(),
        'data': summary_data
    }

    return render_template('teacher/attendance_summary.html',
                          teacher=teacher,
                          summary=summary,
                          dates=date_range)


@teacher_routes.route('/attendance/confirm', methods=['POST'])
def attendance_confirm():
    teacher, redirect_resp = _require_teacher()
    if redirect_resp:
        return redirect_resp

    try:
        payload = request.get_json(force=True)
    except Exception:
        payload = None

    if not payload:
        return json.dumps({'error':'invalid payload'}), 400, {'Content-Type':'application/json'}

    class_id = int(payload.get('class_id')) if payload.get('class_id') else None
    start = payload.get('start')
    period = payload.get('period', 'week')
    days = int(payload.get('days', 6))
    confirm = bool(payload.get('confirm', True))

    if not class_id or not start:
        return json.dumps({'error':'missing params'}), 400, {'Content-Type':'application/json'}

    # permission
    assignments = TeacherAssignment.query.filter_by(teacher_id=teacher.id).all()
    if class_id and not any(a.class_id == class_id for a in assignments):
        return json.dumps({'error':'not allowed'}), 403, {'Content-Type':'application/json'}

    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date()
    except Exception:
        return json.dumps({'error':'invalid date'}), 400, {'Content-Type':'application/json'}

    if period == 'week':
        end_date = start_date + timedelta(days=days-1)
    else:
        end_date = (start_date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    existing = PeriodConfirmation.query.filter_by(class_id=class_id, start_date=start_date, period_type=period, days=days).first()
    if confirm:
        if existing:
            # already confirmed
            return json.dumps({'ok':True, 'confirmed':True}), 200, {'Content-Type':'application/json'}
        pc = PeriodConfirmation(class_id=class_id, start_date=start_date, end_date=end_date, period_type=period, days=days, confirmed_by=teacher.id, confirmed_at=datetime.utcnow())
        db.session.add(pc)
        db.session.commit()
        return json.dumps({'ok':True, 'confirmed':True}), 200, {'Content-Type':'application/json'}
    else:
        if existing:
            db.session.delete(existing)
            db.session.commit()
        return json.dumps({'ok':True, 'confirmed':False}), 200, {'Content-Type':'application/json'}