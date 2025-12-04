"""Debug script to POST to mark-paid endpoint and inspect DB."""
from app import app, db
from models.user_models import User, Role
from models.salary_models import SalaryPayment, RoleSalary
import json

with app.app_context():
    # find a user to test
    user = db.session.query(User).first()
    if not user:
        print('No user found in DB')
        exit(1)

    user_id = user.id
    print('Testing user:', user_id, user.first_name, user.last_name, 'role:', getattr(user.role,'role_name',None))

    client = app.test_client()
    payload = {
        'amount': float(getattr(user,'salary_amount', None) or 500000),
        'period_month': 12,
        'period_year': 2025,
        'reference': 'TEST-REF',
        'notes': 'Debug test'
    }

    resp = client.post(f'/bursar/staff/{user_id}/mark-paid', json=payload)
    print('Status code:', resp.status_code)
    try:
        print('Response JSON:', resp.get_json())
    except Exception as e:
        print('Response content:', resp.data)

    # list last 5 payments for the user
    payments = SalaryPayment.query.filter_by(user_id=user_id).order_by(SalaryPayment.payment_date.desc()).limit(5).all()
    print('Last payments:')
    for p in payments:
        print(p.id, p.amount, p.period_month, p.period_year, p.status, p.reference, p.notes)

    # also show role salary
    if user.role_id:
        rs = RoleSalary.query.filter_by(role_id=user.role_id).first()
        print('RoleSalary for user role:', rs.amount if rs else 'None')

print('Done')
