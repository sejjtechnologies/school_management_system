from flask import Blueprint, render_template, jsonify, request
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import func

from models.user_models import db
from models.user_models import User, Role
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream
from models.salary_models import SalaryPayment, RoleSalary
from models.staff_models import StaffAttendance, StaffProfile, SalaryHistory


headteacher_routes = Blueprint("headteacher_routes", __name__)


@headteacher_routes.route("/headteacher/dashboard")
def dashboard():
    # Fetch role salary defaults to display and allow editing from the dashboard
    role_salaries = []
    try:
        rs_rows = RoleSalary.query.join(Role, RoleSalary.role_id == Role.id).all()
        for r in rs_rows:
            role_salaries.append({
                'id': r.id,
                'role_id': r.role_id,
                'role_name': getattr(r.role, 'role_name', None),
                'amount': str(r.amount) if getattr(r, 'amount', None) is not None else None,
                'min_amount': str(r.min_amount) if getattr(r, 'min_amount', None) is not None else None,
                'max_amount': str(r.max_amount) if getattr(r, 'max_amount', None) is not None else None,
            })
    except Exception:
        # silently ignore DB issues here; template can handle empty list
        role_salaries = []

    return render_template("headteacher/dashboard.html", role_salaries=role_salaries)


@headteacher_routes.route('/headteacher/attendance_summary')
def attendance_summary():
    """Render the attendance summary page for querying attendance over ranges."""
    return render_template('headteacher/attendance_summary.html')


@headteacher_routes.route('/headteacher/api/summary')
def api_summary():
    # Total pupils
    total_pupils = db.session.query(func.count(Pupil.id)).scalar() or 0

    # Total staff (users excluding the 'Pupil' role if present)
    # exclude roles that are not staff (Pupil, Parent) from staff counts
    excluded_roles = []
    pupil_role = Role.query.filter_by(role_name='Pupil').first()
    if pupil_role: excluded_roles.append(pupil_role.id)
    parent_role = Role.query.filter_by(role_name='Parent').first()
    if parent_role: excluded_roles.append(parent_role.id)
    if excluded_roles:
        total_staff = db.session.query(func.count(User.id)).filter(~User.role_id.in_(excluded_roles)).scalar() or 0
    else:
        total_staff = db.session.query(func.count(User.id)).scalar() or 0

    # Pupils by class
    pupils_by_class = []
    cls_counts = (
        db.session.query(Class.id, Class.name, func.count(Pupil.id))
        .join(Pupil, Pupil.class_id == Class.id)
        .group_by(Class.id, Class.name)
        .all()
    )
    for cid, cname, cnt in cls_counts:
        pupils_by_class.append({'class_id': cid, 'class_name': cname, 'count': int(cnt)})

    # Pupils by stream
    pupils_by_stream = []
    stream_counts = (
        db.session.query(Stream.id, Stream.name, func.count(Pupil.id))
        .join(Pupil, Pupil.stream_id == Stream.id)
        .group_by(Stream.id, Stream.name)
        .all()
    )
    for sid, sname, cnt in stream_counts:
        pupils_by_stream.append({'stream_id': sid, 'stream_name': sname, 'count': int(cnt)})

    # Salary payments summary
    salary_count = db.session.query(func.count(SalaryPayment.id)).scalar() or 0
    salary_total = db.session.query(func.coalesce(func.sum(SalaryPayment.amount), 0)).scalar() or 0

    return jsonify({
        'total_pupils': int(total_pupils),
        'total_staff': int(total_staff),
        'pupils_by_class': pupils_by_class,
        'pupils_by_stream': pupils_by_stream,
        'salary_payments_count': int(salary_count),
        'salary_payments_total': str(salary_total),
    })


@headteacher_routes.route('/headteacher/api/staff')
def api_staff():
    # Return all users with role name and staff profile (if any)
    # Return only staff users (exclude pupils if the Pupil role exists)
    # Exclude non-staff roles from the staff listing (Pupil and Parent)
    pupil_role = Role.query.filter_by(role_name='Pupil').first()
    parent_role = Role.query.filter_by(role_name='Parent').first()
    excluded = []
    if pupil_role: excluded.append(pupil_role.id)
    if parent_role: excluded.append(parent_role.id)
    users_q = db.session.query(User, Role).outerjoin(Role, User.role_id == Role.id)
    if excluded:
        users_q = users_q.filter(~User.role_id.in_(excluded))
    users = users_q.all()

    out = []
    for user, role in users:
        profile = StaffProfile.query.filter_by(staff_id=user.id).first()
        latest_payment = (
            SalaryPayment.query.filter_by(user_id=user.id)
            .order_by(SalaryPayment.payment_date.desc())
            .first()
        )
        out.append({
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'role': role.role_name if role else None,
            'salary_override': str(user.salary_amount) if user.salary_amount is not None else None,
            'profile': {
                'bank_name': profile.bank_name if profile else None,
                'bank_account': profile.bank_account if profile else None,
                'tax_id': profile.tax_id if profile else None,
                'pay_grade': profile.pay_grade if profile else None,
            },
            'latest_payment': {
                'id': latest_payment.id,
                'amount': str(latest_payment.amount),
                'date': latest_payment.payment_date.isoformat() if latest_payment else None,
                'status': latest_payment.status if latest_payment else None,
            } if latest_payment else None
        })

    return jsonify(out)


@headteacher_routes.route('/headteacher/api/salary_payments', methods=['GET', 'POST'])
def api_salary_payments():
    if request.method == 'GET':
        payments = SalaryPayment.query.order_by(SalaryPayment.payment_date.desc()).all()
        out = []
        for p in payments:
            out.append({
                'id': p.id,
                'user_id': p.user_id,
                'role_id': p.role_id,
                'amount': str(p.amount),
                'paid_by_user_id': p.paid_by_user_id,
                'payment_date': p.payment_date.isoformat() if p.payment_date else None,
                'period_month': p.period_month,
                'period_year': p.period_year,
                'term': p.term,
                'year': p.year,
                'status': p.status,
                'reference': p.reference,
                'notes': p.notes,
                'payment_method': p.payment_method,
                'bank_name': p.bank_name,
            })
        return jsonify(out)

    # POST - create a salary payment
    data = request.json or {}
    user_id = data.get('user_id')
    amount = data.get('amount')
    if not user_id or amount is None:
        return jsonify({'error': 'user_id_and_amount_required'}), 400

    try:
        amt = Decimal(str(amount))
    except Exception:
        return jsonify({'error': 'invalid_amount'}), 400

    p = SalaryPayment(
        user_id=user_id,
        amount=amt,
        paid_by_user_id=data.get('paid_by_user_id'),
        payment_method=data.get('payment_method'),
        bank_name=data.get('bank_name'),
        reference=data.get('reference'),
        notes=data.get('notes'),
        period_month=data.get('period_month'),
        period_year=data.get('period_year'),
        term=data.get('term'),
        year=data.get('year'),
        status=data.get('status') or 'paid'
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({
        'id': p.id,
        'user_id': p.user_id,
        'amount': str(p.amount),
        'payment_date': p.payment_date.isoformat() if p.payment_date else None,
        'status': p.status,
    }), 201


@headteacher_routes.route('/headteacher/api/salary_payments/<int:payment_id>', methods=['PUT'])
def api_update_salary_payment(payment_id):
    data = request.json or {}
    p = SalaryPayment.query.get(payment_id)
    if not p:
        return jsonify({'error': 'payment_not_found'}), 404

    changed = False
    # Fields allowed to update
    allowed = ['amount', 'status', 'reference', 'notes', 'payment_method', 'bank_name', 'period_month', 'period_year', 'term', 'year']
    for k in allowed:
        if k in data:
            val = data[k]
            # convert numeric fields
            if k == 'amount' and val is not None:
                try:
                    p.amount = val
                except Exception:
                    pass
            else:
                setattr(p, k, val)
            changed = True

    if changed:
        p.updated_at = datetime.utcnow()
        db.session.add(p)
        db.session.commit()

    return jsonify({'status': 'ok', 'id': p.id})


@headteacher_routes.route('/headteacher/api/attendance', methods=['GET', 'POST'])
def api_attendance():
    if request.method == 'GET':
        # optional date param
        d = request.args.get('date')
        if d:
            try:
                qdate = datetime.strptime(d, '%Y-%m-%d').date()
            except Exception:
                return jsonify({'error': 'invalid_date_format'}), 400
        else:
            qdate = date.today()

        rows = StaffAttendance.query.filter_by(date=qdate).all()
        out = []
        for r in rows:
            out.append({
                'id': r.id,
                'staff_id': r.staff_id,
                'date': r.date.isoformat(),
                'status': r.status,
                'recorded_by': r.recorded_by,
                'notes': r.notes,
                'term': getattr(r, 'term', None),
                'year': getattr(r, 'year', None),
                'created_at': r.created_at.isoformat() if getattr(r, 'created_at', None) else None,
                'updated_at': r.updated_at.isoformat() if getattr(r, 'updated_at', None) else None,
            })
        return jsonify(out)

    # POST - create or update
    payload = request.json or {}
    staff_id = payload.get('staff_id')
    d = payload.get('date')
    status = payload.get('status')
    recorded_by = payload.get('recorded_by')
    notes = payload.get('notes')

    if not staff_id or not d or not status:
        return jsonify({'error': 'missing_required'}), 400
    try:
        qdate = datetime.strptime(d, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'invalid_date_format'}), 400
    # optional term/year
    term = payload.get('term')
    year = payload.get('year')

    rec = StaffAttendance.query.filter_by(staff_id=staff_id, date=qdate).first()
    if rec:
        rec.status = status
        rec.recorded_by = recorded_by or rec.recorded_by
        rec.notes = notes or rec.notes
        if term is not None: rec.term = term
        if year is not None: rec.year = year
        rec.updated_at = datetime.utcnow()
    else:
        rec = StaffAttendance(
            staff_id=staff_id,
            date=qdate,
            status=status,
            recorded_by=recorded_by,
            notes=notes,
            term=term,
            year=year,
        )
        db.session.add(rec)

    db.session.commit()
    return jsonify({'status': 'ok', 'id': rec.id})


@headteacher_routes.route('/headteacher/api/attendance/aggregate', methods=['GET'])
def api_attendance_aggregate():
    """Aggregate attendance counts per staff over a date range.
    Query params:
      start=YYYY-MM-DD (required)
      end=YYYY-MM-DD (optional; defaults to start)
      term (optional)
      year (optional)
    Returns JSON: { start, end, days_in_range, results: [{id, first_name, last_name, role, present_count}] }
    """
    from sqlalchemy import func, case
    start_s = request.args.get('start')
    end_s = request.args.get('end') or start_s
    if not start_s:
        return jsonify({'error': 'start_date_required'}), 400
    try:
        start_date = datetime.strptime(start_s, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_s, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'invalid_date_format'}), 400

    if end_date < start_date:
        return jsonify({'error': 'end_before_start'}), 400

    term = request.args.get('term')
    year = request.args.get('year')

    # Build counts subquery: present_count per staff
    present_sum = func.coalesce(func.sum(case([(StaffAttendance.status == 'present', 1)], else_=0)), 0).label('present_count')
    counts_q = db.session.query(StaffAttendance.staff_id.label('staff_id'), present_sum)
    counts_q = counts_q.filter(StaffAttendance.date >= start_date, StaffAttendance.date <= end_date)
    if term:
        counts_q = counts_q.filter(StaffAttendance.term == term)
    if year:
        try:
            yv = int(year)
            counts_q = counts_q.filter(StaffAttendance.year == yv)
        except Exception:
            pass
    counts_q = counts_q.group_by(StaffAttendance.staff_id).subquery()

    # Exclude Pupil and Parent roles from staff listing (consistent with api_staff)
    pupil_role = Role.query.filter_by(role_name='Pupil').first()
    parent_role = Role.query.filter_by(role_name='Parent').first()
    excluded = []
    if pupil_role: excluded.append(pupil_role.id)
    if parent_role: excluded.append(parent_role.id)

    # Query all users (staff) with their present count (0 when absent from counts_q)
    q = db.session.query(
        User.id.label('id'), User.first_name, User.last_name, Role.role_name.label('role'),
        func.coalesce(counts_q.c.present_count, 0).label('present_count')
    ).outerjoin(Role, User.role_id == Role.id).outerjoin(counts_q, counts_q.c.staff_id == User.id)

    if excluded:
        q = q.filter(~User.role_id.in_(excluded))

    rows = q.order_by(User.first_name, User.last_name).all()

    results = []
    for r in rows:
        results.append({
            'id': r.id,
            'first_name': r.first_name,
            'last_name': r.last_name,
            'role': r.role,
            'present_count': int(r.present_count) if r.present_count is not None else 0,
        })

    days_in_range = (end_date - start_date).days + 1
    return jsonify({
        'start': start_date.isoformat(),
        'end': end_date.isoformat(),
        'days_in_range': days_in_range,
        'results': results,
    })


@headteacher_routes.route('/headteacher/api/attendance/aggregate/explain')
def api_attendance_aggregate_explain():
    """Return EXPLAIN ANALYZE plan for the aggregate attendance query.
    Use this in development to inspect the query plan and identify slow parts.
    Same params as aggregate: start (required), end (optional), term, year
    """
    start_s = request.args.get('start')
    end_s = request.args.get('end') or start_s
    if not start_s:
        return jsonify({'error': 'start_date_required'}), 400
    try:
        start_date = datetime.strptime(start_s, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_s, '%Y-%m-%d').date()
    except Exception:
        return jsonify({'error': 'invalid_date_format'}), 400

    term = request.args.get('term')
    year = request.args.get('year')

    # determine excluded roles
    pupil_role = Role.query.filter_by(role_name='Pupil').first()
    parent_role = Role.query.filter_by(role_name='Parent').first()
    excluded_ids = []
    if pupil_role: excluded_ids.append(pupil_role.id)
    if parent_role: excluded_ids.append(parent_role.id)

    # build raw SQL for explain analyze
    params = {'start_date': start_date, 'end_date': end_date}
    where_clauses = ["sa.date >= :start_date", "sa.date <= :end_date"]
    if term:
        where_clauses.append("sa.term = :term")
        params['term'] = term
    if year:
        where_clauses.append("sa.year = :year")
        try:
            params['year'] = int(year)
        except Exception:
            params['year'] = year

    where_sql = ' AND '.join(where_clauses)

    excluded_sql = ''
    if excluded_ids:
        excluded_sql = 'WHERE u.role_id NOT IN (' + ','.join(str(x) for x in excluded_ids) + ')'

    sql = f"""
EXPLAIN ANALYZE
WITH counts AS (
  SELECT sa.staff_id, COALESCE(SUM(CASE WHEN sa.status = 'present' THEN 1 ELSE 0 END),0) AS present_count
  FROM staff_attendance sa
  WHERE {where_sql}
  GROUP BY sa.staff_id
)
SELECT u.id, u.first_name, u.last_name, r.role_name, COALESCE(c.present_count,0) AS present_count
FROM users u
LEFT JOIN counts c ON c.staff_id = u.id
LEFT JOIN roles r ON u.role_id = r.id
{excluded_sql}
ORDER BY u.first_name, u.last_name;
"""

    try:
        res = db.session.execute(text(sql), params)
        plan_rows = [row[0] for row in res.fetchall()]
        return jsonify({'plan': plan_rows})
    except Exception as e:
        return jsonify({'error': 'explain_failed', 'detail': str(e)}), 500


# Batch attendance endpoint: accept an array of attendance records and upsert them in a transaction
@headteacher_routes.route('/headteacher/api/attendance/batch', methods=['POST'])
def api_attendance_batch():
    payload = request.json or []
    if not isinstance(payload, list):
        return jsonify({'error': 'expected_array'}), 400

    results = []
    errors = []
    for idx, item in enumerate(payload):
        staff_id = item.get('staff_id')
        d = item.get('date')
        status = item.get('status')
        recorded_by = item.get('recorded_by')
        notes = item.get('notes')
        term = item.get('term')
        year = item.get('year')

        if not staff_id or not d or not status:
            errors.append({'index': idx, 'error': 'missing_required'})
            continue
        try:
            qdate = datetime.strptime(d, '%Y-%m-%d').date()
        except Exception:
            errors.append({'index': idx, 'error': 'invalid_date_format'})
            continue

        try:
            rec = StaffAttendance.query.filter_by(staff_id=staff_id, date=qdate).first()
            if rec:
                rec.status = status
                rec.recorded_by = recorded_by or rec.recorded_by
                rec.notes = notes or rec.notes
                if term is not None: rec.term = term
                if year is not None: rec.year = year
                rec.updated_at = datetime.utcnow()
            else:
                rec = StaffAttendance(
                    staff_id=staff_id,
                    date=qdate,
                    status=status,
                    recorded_by=recorded_by,
                    notes=notes,
                    term=term,
                    year=year,
                )
                db.session.add(rec)
            db.session.flush()
            results.append({'index': idx, 'id': rec.id})
        except Exception as e:
            db.session.rollback()
            errors.append({'index': idx, 'error': str(e)})
    # commit once after processing all
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'commit_failed', 'detail': str(e)}), 500

    return jsonify({'results': results, 'errors': errors}), 200


# API endpoint to fetch all role salaries for display/editing
@headteacher_routes.route('/headteacher/api/role_salaries', methods=['GET', 'POST', 'PUT'])
def api_role_salaries():
    if request.method == 'GET':
        # Return all role salaries with role info
        role_salaries = []
        try:
            rs_rows = RoleSalary.query.join(Role, RoleSalary.role_id == Role.id).all()
            for r in rs_rows:
                role_salaries.append({
                    'id': r.id,
                    'role_id': r.role_id,
                    'role_name': getattr(r.role, 'role_name', None),
                    'amount': str(r.amount) if getattr(r, 'amount', None) is not None else None,
                    'min_amount': str(r.min_amount) if getattr(r, 'min_amount', None) is not None else None,
                    'max_amount': str(r.max_amount) if getattr(r, 'max_amount', None) is not None else None,
                    'created_at': r.created_at.isoformat() if getattr(r, 'created_at', None) else None,
                    'updated_at': r.updated_at.isoformat() if getattr(r, 'updated_at', None) else None,
                })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        return jsonify({'role_salaries': role_salaries}), 200

    # POST - create new role salary
    if request.method == 'POST':
        data = request.json or {}
        role_id = data.get('role_id')
        amount = data.get('amount')
        if not role_id or amount is None:
            return jsonify({'error': 'role_id_and_amount_required'}), 400

        # Check if role exists
        role = Role.query.get(role_id)
        if not role:
            return jsonify({'error': 'role_not_found'}), 404

        # Check if already exists
        existing = RoleSalary.query.filter_by(role_id=role_id).first()
        if existing:
            return jsonify({'error': 'role_salary_already_exists'}), 400

        try:
            amt = Decimal(str(amount))
            rs = RoleSalary(
                role_id=role_id,
                amount=amt,
                min_amount=Decimal(str(data.get('min_amount', 0))) if data.get('min_amount') else None,
                max_amount=Decimal(str(data.get('max_amount', 0))) if data.get('max_amount') else None,
            )
            db.session.add(rs)
            db.session.commit()
            return jsonify({
                'id': rs.id,
                'role_id': rs.role_id,
                'amount': str(rs.amount),
                'min_amount': str(rs.min_amount) if rs.min_amount else None,
                'max_amount': str(rs.max_amount) if rs.max_amount else None,
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    # PUT - update role salary by id
    if request.method == 'PUT':
        data = request.json or {}
        role_salary_id = data.get('id')
        if not role_salary_id:
            return jsonify({'error': 'id_required'}), 400

        rs = RoleSalary.query.get(role_salary_id)
        if not rs:
            return jsonify({'error': 'role_salary_not_found'}), 404

        try:
            if 'amount' in data and data['amount'] is not None:
                rs.amount = Decimal(str(data['amount']))
            if 'min_amount' in data and data['min_amount'] is not None:
                rs.min_amount = Decimal(str(data['min_amount']))
            if 'max_amount' in data and data['max_amount'] is not None:
                rs.max_amount = Decimal(str(data['max_amount']))

            rs.updated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({
                'id': rs.id,
                'role_id': rs.role_id,
                'amount': str(rs.amount),
                'min_amount': str(rs.min_amount) if rs.min_amount else None,
                'max_amount': str(rs.max_amount) if rs.max_amount else None,
                'updated_at': rs.updated_at.isoformat(),
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
