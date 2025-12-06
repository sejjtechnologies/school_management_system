"""
Render `templates/parent/payment_status.html` using real DB objects to catch template errors.
"""
import os
import sys
from dotenv import load_dotenv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
load_dotenv()
from app import app
from models.register_pupils import Pupil, Payment

with app.app_context():
    pupil = Pupil.query.first()
    if not pupil:
        print('No pupil found in DB; aborting test')
        sys.exit(0)
    payments = Payment.query.filter_by(pupil_id=pupil.id).all()
    payments_data = []
    for p in payments:
        payments_data.append({
            'id': p.id,
            'fee_id': p.fee_id,
            'amount_paid': p.amount_paid,
            'amount': p.amount_paid or 0,
            'payment_date': p.payment_date,
            'date_created': p.payment_date,
            'payment_method': p.payment_method,
            'reference': p.reference,
            'transaction_id': p.reference or p.id,
            'status': p.status,
            'description': p.description,
            'year': p.year,
            'term': p.term,
            'fee_item_name': getattr(p.fee_item, 'item_name', None),
            'fee_item_required': getattr(p.fee_item, 'amount', None)
        })
    summary = {'outstanding': 0, 'paid': sum(p['amount_paid'] for p in payments_data), 'total': sum(p['amount_paid'] for p in payments_data)}
    tmpl = app.jinja_env.get_template('parent/payment_status.html')
    # Render inside a test request context so url_for() and other request-bound
    # helpers work during template rendering.
    try:
        with app.test_request_context():
            out = tmpl.render(pupil=pupil, payments=payments_data, summary=summary)
            print('Rendered successfully; length=', len(out))
    except Exception as e:
        print('Template rendering failed with exception:')
        import traceback
        traceback.print_exc()
        sys.exit(1)

print('Done')
