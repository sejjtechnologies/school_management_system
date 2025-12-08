from flask import Blueprint, render_template, jsonify, request
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import func

from models.user_models import db
from models.user_models import User, Role
from models.register_pupils import Pupil
from models.class_model import Class
from models.stream_model import Stream
from models.salary_models import SalaryPayment
from models.staff_models import StaffAttendance, StaffProfile, SalaryHistory


headteacher_routes = Blueprint("headteacher_routes", __name__)


@headteacher_routes.route("/headteacher/dashboard")
def dashboard():
    return render_template("headteacher/dashboard.html")


@headteacher_routes.route('/headteacher/api/summary')
def api_summary():
    # Total pupils
    total_pupils = db.session.query(func.count(Pupil.id)).scalar() or 0

    # Total staff (users excluding the 'Pupil' role if present)
    pupil_role = Role.query.filter_by(role_name='Pupil').first()
    if pupil_role:
        total_staff = db.session.query(func.count(User.id)).filter(User.role_id != pupil_role.id).scalar() or 0
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
    pupil_role = Role.query.filter_by(role_name='Pupil').first()
    users_q = db.session.query(User, Role).outerjoin(Role, User.role_id == Role.id)
    if pupil_role:
        users_q = users_q.filter(User.role_id != pupil_role.id)
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
