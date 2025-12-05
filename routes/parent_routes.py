from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from models.user_models import db, User, Role
from models.term_model import Term
from models.register_pupils import Pupil, Payment
from models.timetable_model import TimeTableSlot
from models.attendance_model import Attendance
from models.marks_model import Mark, Subject, Report, Exam
from models.class_model import Class
from models.stream_model import Stream
from models.teacher_assignment_models import TeacherAssignment
from sqlalchemy import or_

parent_routes = Blueprint("parent_routes", __name__)


def _parent_authorized_for_pupil(user, pupil):
    """Return True if the user (parent) is allowed to view the pupil's data.

    The project schema does not appear to have a formal parent->pupil FK, so
    we use a best-effort check: email match, guardian_name contains parent's
    first/last name, or a pupil selected in session during search.
    """
    if not user or not pupil:
        return False

    try:
        if getattr(pupil, 'email', None) and getattr(user, 'email', None):
            if pupil.email.lower() == user.email.lower():
                return True
    except Exception:
        pass

    try:
        guardian_name = (getattr(pupil, 'guardian_name', '') or '')
        if guardian_name and (getattr(user, 'first_name', None) and user.first_name and user.first_name.lower() in guardian_name.lower() or getattr(user, 'last_name', None) and user.last_name and user.last_name.lower() in guardian_name.lower()):
            return True
    except Exception:
        pass

    try:
        sel = session.get('parent_selected_pupil_id')
        if sel and int(sel) == int(pupil.id):
            return True
    except Exception:
        pass

    return False


@parent_routes.route("/parent/dashboard")
def dashboard():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to access the parent dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    user = User.query.get(user_id)
    if not user or not user.role or user.role.role_name.lower() != "parent":
        flash("Access denied. Only parents can view this dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    return render_template("parent/dashboard.html", parent=user)


@parent_routes.route("/parent/pupil/<int:pupil_id>/dashboard")
def pupil_dashboard(pupil_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to access the parent dashboard.", "danger")
        return redirect(url_for("user_routes.login"))

    user = User.query.get(user_id)
    pupil = Pupil.query.get_or_404(pupil_id)

    if not _parent_authorized_for_pupil(user, pupil):
        flash('Access denied. You can only view your own child.', 'danger')
        return redirect(url_for('parent_routes.dashboard'))

    return render_template('parent/pupil_dashboard.html', parent=user, pupil=pupil)


@parent_routes.route("/api/parent/search-child")
def api_parent_search_child():
    """Search pupils for parent dashboard autocomplete/search box.

    Returns JSON {pupils: [...]}. Query param: q
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = User.query.get(user_id)
    if not user or not user.role or user.role.role_name.lower() != 'parent':
        return jsonify({"error": "Access denied"}), 403

    search_query = request.args.get('q', '').strip()
    if not search_query or len(search_query) < 2:
        return jsonify({"error": "Search query too short"}), 400

    try:
        like_q = f"%{search_query}%"
        pupils = Pupil.query.filter(
            or_(
                Pupil.first_name.ilike(like_q),
                Pupil.middle_name.ilike(like_q),
                Pupil.last_name.ilike(like_q),
                Pupil.admission_number.ilike(like_q),
                Pupil.pupil_id.ilike(like_q),
                Pupil.roll_number.ilike(like_q),
            )
        ).limit(20).all()

        if not pupils:
            return jsonify({"error": "No pupils found"}), 404

        results = []
        for p in pupils:
            parts = [p.first_name or "", p.middle_name or "", p.last_name or ""]
            full_name = " ".join([pp.strip() for pp in parts if pp and pp.strip()])
            class_name = getattr(p, 'class_', None)
            class_name = getattr(class_name, 'name', None) if class_name else None
            stream = getattr(p, 'stream', None)
            stream_name = getattr(stream, 'name', None) if stream else None

            results.append({
                'id': p.id,
                'name': full_name,
                'admission_number': p.admission_number,
                'pupil_id': p.pupil_id,
                'roll_number': p.roll_number,
                'class_id': p.class_id,
                'class_name': class_name,
                'stream_id': p.stream_id,
                'stream_name': stream_name,
                'status': getattr(p, 'enrollment_status', None) or getattr(p, 'status', None) or 'Active'
            })

        # store first result in session for UX convenience
        try:
            if results:
                session['parent_selected_pupil_id'] = results[0]['id']
        except Exception:
            pass

        return jsonify({'pupils': results}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@parent_routes.route("/api/parent/pupil/<int:pupil_id>/attendance-summary", methods=["GET"])
def attendance_summary_api(pupil_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    pupil = Pupil.query.get_or_404(pupil_id)
    user = User.query.get(user_id)
    if not _parent_authorized_for_pupil(user, pupil):
        return jsonify({"error": "Access denied"}), 403

    period = request.args.get('period', 'week')
    date_str = request.args.get('date')
    from datetime import datetime, date, timedelta

    try:
        ref_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    except Exception:
        ref_date = date.today()

    if period == 'day':
        start_date = end_date = ref_date
    elif period == 'week':
        start_date = ref_date - timedelta(days=ref_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = ref_date.replace(day=1)
        if ref_date.month == 12:
            next_month = ref_date.replace(year=ref_date.year + 1, month=1, day=1)
        else:
            next_month = ref_date.replace(month=ref_date.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
    else:
        term = Term.query.filter(Term.start_date <= ref_date, Term.end_date >= ref_date).first()
        if term:
            start_date = term.start_date
            end_date = term.end_date
        else:
            end_date = ref_date
            start_date = ref_date - timedelta(days=104)

    records = Attendance.query.filter(
        Attendance.pupil_id == pupil_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    counts = {"present": 0, "absent": 0, "late": 0, "leave": 0}
    for r in records:
        st = (r.status or '').lower()
        if st in counts:
            counts[st] += 1

    teacher_records = Attendance.query.join(User, Attendance.recorded_by == User.id).join(Role).filter(
        Role.role_name.ilike('teacher'),
        Attendance.pupil_id == pupil_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    teacher_total = len(teacher_records)
    teacher_counts = {"present": 0, "absent": 0, "late": 0, "leave": 0}
    for r in teacher_records:
        st = (r.status or '').lower()
        if st in teacher_counts:
            teacher_counts[st] += 1

    rec_list = [{"date": r.date.isoformat(), "status": r.status, "reason": r.reason, "recorded_by": r.recorded_by} for r in records[:200]]

    return jsonify({
        "pupil_id": pupil_id,
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_records": len(records),
        "counts": counts,
        "teacher_records_total": teacher_total,
        "teacher_counts": teacher_counts,
        "records_sample": rec_list
    })


@parent_routes.route("/parent/pupil/<int:pupil_id>/timetable")
def view_timetable(pupil_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)
    user = User.query.get(user_id)
    if not _parent_authorized_for_pupil(user, pupil):
        flash('Access denied. You can only view timetables for your own child.', 'danger')
        return redirect(url_for('parent_routes.dashboard'))

    timetable = TimeTableSlot.query.filter_by(class_id=pupil.class_id, stream_id=pupil.stream_id).all()
    schedule = {}
    for slot in timetable:
        if not getattr(slot, 'teacher', None) or not getattr(slot, 'subject', None):
            continue
        day = slot.day_of_week
        schedule.setdefault(day, []).append({
            'start_time': slot.start_time,
            'end_time': slot.end_time,
            'subject': slot.subject.name if slot.subject else None,
            'teacher': f"{getattr(slot.teacher, 'first_name', '')} {getattr(slot.teacher, 'last_name', '')}".strip(),
            'classroom': getattr(slot, 'classroom', None)
        })

    assignment = TeacherAssignment.query.filter_by(class_id=pupil.class_id, stream_id=pupil.stream_id).first()
    class_teacher = f"{assignment.teacher.first_name} {assignment.teacher.last_name}".strip() if assignment and getattr(assignment, 'teacher', None) else None

    return render_template('parent/timetable.html', pupil=pupil, schedule=schedule, class_teacher=class_teacher)


@parent_routes.route("/parent/pupil/<int:pupil_id>/attendance")
def view_attendance(pupil_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("user_routes.login"))

    pupil = Pupil.query.get_or_404(pupil_id)
    user = User.query.get(user_id)
    if not _parent_authorized_for_pupil(user, pupil):
        flash('Access denied. You can only view your own child.', 'danger')
        return redirect(url_for('parent_routes.dashboard'))

    period = request.args.get('period', 'week')
    date_str = request.args.get('date')
    from datetime import datetime, date, timedelta
    try:
        ref_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    except Exception:
        ref_date = date.today()

    if period == 'day':
        start_date = end_date = ref_date
    elif period == 'week':
        start_date = ref_date - timedelta(days=ref_date.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = ref_date.replace(day=1)
        if ref_date.month == 12:
            next_month = ref_date.replace(year=ref_date.year + 1, month=1, day=1)
        else:
            next_month = ref_date.replace(month=ref_date.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
    else:
        term = Term.query.filter(Term.start_date <= ref_date, Term.end_date >= ref_date).first()
        if term:
            start_date = term.start_date
            end_date = term.end_date
        else:
            end_date = ref_date
            start_date = ref_date - timedelta(days=104)

    attendance_records = Attendance.query.filter(Attendance.pupil_id == pupil_id, Attendance.date >= start_date, Attendance.date <= end_date).order_by(Attendance.date.asc()).all()
    total_days = len(attendance_records)
    present_days = len([a for a in attendance_records if a.status and a.status.lower() == 'present'])
    absent_days = len([a for a in attendance_records if a.status and a.status.lower() == 'absent'])
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    return render_template('parent/attendance.html', pupil=pupil, attendance_records=attendance_records, stats={'total': total_days, 'present': present_days, 'absent': absent_days, 'percentage': round(attendance_percentage,1)}, period=period, date=ref_date.isoformat(), start_date=start_date, end_date=end_date)


@parent_routes.route("/parent/pupil/<int:pupil_id>/reports")
def view_reports(pupil_id):
    """Show academic reports for a pupil. Supports filtering by term, exam_set(name) and year via query params."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user_routes.login'))

    pupil = Pupil.query.get_or_404(pupil_id)
    user = User.query.get(user_id)
    if not _parent_authorized_for_pupil(user, pupil):
        flash('Access denied. You can only view your own child.', 'danger')
        return redirect(url_for('parent_routes.dashboard'))

    # Filters
    selected_term = request.args.get('term', type=int)
    selected_exam_set = request.args.get('exam_set', default=None, type=str)
    selected_year = request.args.get('year', type=int)

    # Query available exam options from DB (e.g., Midterm, End Term)
    all_exams = Exam.query.order_by(Exam.year.desc(), Exam.term.asc()).all()
    available_terms = sorted({e.term for e in all_exams if e.term is not None})
    # Show all distinct years found in the Exam table (cast safely to int)
    years_set = set()
    for e in all_exams:
        y = getattr(e, 'year', None)
        try:
            yi = int(y) if y is not None else None
        except Exception:
            yi = None
        if yi is not None:
            years_set.add(yi)
    available_years = sorted(years_set, reverse=True)
    available_exam_sets = sorted({e.name for e in all_exams if e.name})

    # Fetch Report rows for pupil based on selected filters.
    # IMPORTANT: do NOT recalculate or aggregate here — read values that were
    # pre-computed and stored in the Report model (total_score, average_score,
    # stream_position, class_position, remarks, general_remark, etc.).
    rpt_q = Report.query.filter(Report.pupil_id == pupil_id).join(Exam)
    if selected_term:
        rpt_q = rpt_q.filter(Exam.term == selected_term)
    if selected_exam_set:
        rpt_q = rpt_q.filter(Exam.name == selected_exam_set)
    if selected_year:
        rpt_q = rpt_q.filter(Exam.year == selected_year)
    filtered_reports = rpt_q.order_by(Exam.year.desc(), Exam.term.asc(), Exam.name.asc()).all()

    # Build list of report dicts to pass to template. Include associated marks
    # for each report (subject-level scores) but do not perform any arithmetic.
    filtered_data = []
    for report in filtered_reports:
        exam = getattr(report, 'exam', None)

        # Fetch marks for THIS exam only (raw DB values)
        marks_for_exam = []
        try:
            marks_rows = Mark.query.filter_by(pupil_id=pupil_id, exam_id=getattr(exam, 'id', None)).all()
            for mr in marks_rows:
                marks_for_exam.append({
                    'subject': getattr(mr.subject, 'name', None) if getattr(mr, 'subject', None) else None,
                    'score': getattr(mr, 'score', None),
                    'weight': getattr(mr.subject, 'weight', None) if getattr(mr, 'subject', None) else None,
                    'percentage': getattr(mr, 'percentage', None) if hasattr(mr, 'percentage') else None,
                    'grade': getattr(mr, 'grade', None) if hasattr(mr, 'grade') else None
                })
        except Exception:
            marks_for_exam = []

        filtered_data.append({
            'exam_id': getattr(exam, 'id', None),
            'term': getattr(exam, 'term', None),
            'exam_set': getattr(exam, 'name', None),
            'year': getattr(exam, 'year', None),
            'report_id': getattr(report, 'id', None),
            'total_score': getattr(report, 'total_score', None),
            'average_score': getattr(report, 'average_score', None),
            'grade': getattr(report, 'grade', None),
            'remarks': getattr(report, 'remarks', None),
            'stream_position': getattr(report, 'stream_position', None),
            'class_position': getattr(report, 'class_position', None),
            'combined_position': getattr(report, 'combined_position', None),
            'teacher_comment': getattr(report, 'general_remark', None),
            'general_remark': getattr(report, 'general_remark', None),
            'awards': getattr(report, 'awards', None) if hasattr(report, 'awards') else None,
            'marks': marks_for_exam
        })

    # Build term-level reports (all exam sets for the selected term/year) so the
    # template can show a "term summary" composed of the stored Report rows.
    term_reports = []
    if selected_term and selected_year:
        try:
            term_rows = Report.query.join(Exam).filter(
                Report.pupil_id == pupil_id,
                Exam.term == selected_term,
                Exam.year == selected_year
            ).order_by(Exam.name.asc()).all()
            for tr in term_rows:
                ex = getattr(tr, 'exam', None)
                term_reports.append({
                    'exam_set': getattr(ex, 'name', None),
                    'report_id': getattr(tr, 'id', None),
                    'total_score': getattr(tr, 'total_score', None),
                    'average_score': getattr(tr, 'average_score', None),
                    'stream_position': getattr(tr, 'stream_position', None),
                    'class_position': getattr(tr, 'class_position', None),
                    'combined_position': getattr(tr, 'combined_position', None),
                    'remarks': getattr(tr, 'remarks', None),
                    'teacher_comment': getattr(tr, 'general_remark', None)
                })
        except Exception:
            term_reports = []

    # Build combined term summary (aggregate across all exam sets in the
    # selected term/year) for the pupil's class and stream. We compute the
    # combined total per pupil across the reports in that term and rank them
    # within class and within stream. Prefer stored Report fields when
    # available, but aggregate when needed to produce a term-level ranking.
    combined_summary = None
    if selected_term and selected_year:
        try:
            # Exams in this term/year
            exams_in_term = Exam.query.filter(Exam.term == selected_term, Exam.year == selected_year).all()
            exam_ids = [e.id for e in exams_in_term if getattr(e, 'id', None) is not None]

            # All reports in the term/year (for all pupils) used for ranking
            term_all_reports = Report.query.join(Exam).join(Pupil).filter(
                Exam.term == selected_term,
                Exam.year == selected_year
            ).all()

            # Build sets of pupil ids by class and by stream (only those with reports)
            class_pupil_ids = set()
            stream_pupil_ids = set()
            for r in term_all_reports:
                p = getattr(r, 'pupil', None)
                if not p:
                    continue
                if getattr(p, 'class_id', None) == getattr(pupil, 'class_id', None):
                    class_pupil_ids.add(p.id)
                if getattr(p, 'stream_id', None) == getattr(pupil, 'stream_id', None):
                    stream_pupil_ids.add(p.id)

            # Helper: compute combined total_score per pupil (sum of Report.total_score)
            class_totals = {}
            stream_totals = {}
            class_counts = {}
            for r in term_all_reports:
                pid = r.pupil_id
                ts = getattr(r, 'total_score', 0) or 0
                p = getattr(r, 'pupil', None)
                if not p:
                    continue
                if pid in class_pupil_ids:
                    class_totals[pid] = class_totals.get(pid, 0) + ts
                    class_counts[pid] = class_counts.get(pid, 0) + 1
                if pid in stream_pupil_ids:
                    stream_totals[pid] = stream_totals.get(pid, 0) + ts

            class_count = len(class_totals)
            stream_count = len(stream_totals)

            # Ranking function (competition style)
            def compute_rankings(totals_dict):
                sorted_items = sorted(totals_dict.items(), key=lambda kv: kv[1], reverse=True)
                ranks = {}
                last_score = None
                last_rank = 0
                idx = 0
                for pid, tot in sorted_items:
                    idx += 1
                    if last_score is None or tot != last_score:
                        last_rank = idx
                        last_score = tot
                    ranks[pid] = last_rank
                return ranks

            class_ranks = compute_rankings(class_totals)
            stream_ranks = compute_rankings(stream_totals)

            # Compute per-pupil weighted average across all marks in the term.
            # Use Subject.weight if present, otherwise default to 1.
            from sqlalchemy import func

            def compute_term_weighted_average(pid):
                # Query all marks for this pupil across the exams in this term
                if not exam_ids:
                    return None
                marks = Mark.query.join(Subject).filter(Mark.pupil_id == pid, Mark.exam_id.in_(exam_ids)).all()
                weight_sum = 0
                weighted_score = 0
                for m in marks:
                    subj = getattr(m, 'subject', None)
                    w = getattr(subj, 'weight', None) if subj is not None else None
                    try:
                        wi = float(w) if w is not None else 1.0
                    except Exception:
                        wi = 1.0
                    s = getattr(m, 'score', None)
                    if s is None:
                        continue
                    weighted_score += (s or 0) * wi
                    weight_sum += wi
                return (weighted_score / weight_sum) if weight_sum > 0 else None

            # For the current pupil compute combined totals and averages
            my_class_total = class_totals.get(pupil.id)
            my_stream_total = stream_totals.get(pupil.id)
            my_class_pos = class_ranks.get(pupil.id)
            my_stream_pos = stream_ranks.get(pupil.id)
            my_sets = class_counts.get(pupil.id) or 0
            my_weighted_avg = compute_term_weighted_average(pupil.id)

            # Aggregate teacher comments / remarks from the pupil's term_reports (per set)
            pupil_teacher_comments = [tr.get('teacher_comment') for tr in term_reports if tr.get('teacher_comment')]
            pupil_remarks = [tr.get('remarks') for tr in term_reports if tr.get('remarks')]

            combined_summary = {
                'combined_total': my_class_total,
                'combined_sets': my_sets,
                'combined_average': my_weighted_avg if my_weighted_avg is not None else ((my_class_total / my_sets) if my_class_total is not None and my_sets > 0 else None),
                'class_position': my_class_pos,
                'class_count': class_count,
                'stream_position': my_stream_pos,
                'stream_count': stream_count,
                'combined_teacher_comments': pupil_teacher_comments,
                'combined_remarks': pupil_remarks
            }
        except Exception:
            combined_summary = None

    # Counts for stream/class (for display only, do not use to compute positions)
    stream_count = Pupil.query.filter_by(stream_id=pupil.stream_id).count() if getattr(pupil, 'stream_id', None) else None
    class_count = Pupil.query.filter_by(class_id=pupil.class_id).count() if getattr(pupil, 'class_id', None) else None

    # Build a simple subject->score map for the first (selected) report so the
    # template can show a per-subject listing. We intentionally do not perform
    # any arithmetic beyond reading stored mark rows attached to the Report.
    subject_marks = {}
    average_score_400 = None
    if filtered_data:
        first = filtered_data[0]
        marks_list = first.get('marks') or []
        for m in marks_list:
            subj = m.get('subject') if isinstance(m, dict) else None
            if subj:
                subject_marks[subj] = m.get('score')

        # Prefer total_score if present, otherwise use average_score as a
        # display value. We do NOT recalculate or scale values here.
        if first.get('total_score') is not None:
            average_score_400 = first.get('total_score')
        elif first.get('average_score') is not None:
            average_score_400 = first.get('average_score')

    return render_template('parent/reports.html',
                           pupil=pupil,
                           filtered_data=filtered_data,
                           term_reports=term_reports,
                           available_terms=available_terms,
                           available_years=available_years,
                           available_exam_sets=available_exam_sets,
                           selected_term=selected_term,
                           selected_exam_set=selected_exam_set,
                           selected_year=selected_year,
                           stream_count=stream_count,
                           class_count=class_count,
                           subject_marks=subject_marks,
                           average_score_400=average_score_400,
                           combined_summary=combined_summary)


@parent_routes.route("/parent/pupil/<int:pupil_id>/payments")
def view_payments(pupil_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user_routes.login'))

    pupil = Pupil.query.get_or_404(pupil_id)
    user = User.query.get(user_id)
    if not _parent_authorized_for_pupil(user, pupil):
        flash('Access denied.', 'danger')
        return redirect(url_for('parent_routes.dashboard'))

    payments = Payment.query.filter_by(pupil_id=pupil_id).all()
    total_pending = sum(getattr(p, 'amount', 0) for p in payments if getattr(p, 'status', None) == 'pending')
    total_paid = sum(getattr(p, 'amount', 0) for p in payments if getattr(p, 'status', None) == 'completed')
    return render_template('parent/payment_status.html', pupil=pupil, payments=payments, summary={'outstanding': total_pending, 'paid': total_paid, 'total': total_pending + total_paid})


@parent_routes.route("/parent/pupil/<int:pupil_id>/balance")
def view_balance(pupil_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user_routes.login'))
    pupil = Pupil.query.get_or_404(pupil_id)
    payments = Payment.query.filter_by(pupil_id=pupil_id).all()
    total_owed = sum(getattr(p, 'amount', 0) for p in payments if getattr(p, 'status', None) == 'pending')
    total_paid = sum(getattr(p, 'amount', 0) for p in payments if getattr(p, 'status', None) == 'completed')
    balance_status = 'Credit' if total_paid > total_owed else 'Debit'
    balance_amount = abs(total_paid - total_owed)
    return render_template('parent/balance.html', pupil=pupil, balance={'status': balance_status, 'amount': balance_amount, 'outstanding': total_owed, 'paid': total_paid})


@parent_routes.route("/parent/pupil/<int:pupil_id>/receipts")
def view_receipts(pupil_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user_routes.login'))
    pupil = Pupil.query.get_or_404(pupil_id)
    receipts = Payment.query.filter_by(pupil_id=pupil_id).all()
    return render_template('parent/receipts.html', pupil=pupil, receipts=receipts)


@parent_routes.route("/parent/receipt/<int:receipt_id>/download")
def download_receipt(receipt_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('user_routes.login'))
    receipt = Payment.query.get_or_404(receipt_id)
    flash('Receipt download not implemented yet.', 'info')
    return redirect(request.referrer or url_for('parent_routes.dashboard'))
"""
NOTE: The rest of this file (below) previously contained a duplicated blueprint and duplicated route definitions.
That duplication caused some routes to be registered on a different blueprint object, leading to 404 for
endpoints declared above. The duplicate block has been removed — everything below this docstring is intentionally empty.
If you need to add more routes, add them above this note.
"""