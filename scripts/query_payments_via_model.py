"""
Query payments via SQLAlchemy ORM model in an application context to verify no ProgrammingError.
Usage: python scripts/query_payments_via_model.py
"""
import os
import sys
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

load_dotenv()

from app import app
from models.register_pupils import Payment

with app.app_context():
    payments = Payment.query.limit(5).all()
    print(f"Found {len(payments)} payments via ORM")
    for p in payments:
        print({
            'id': p.id,
            'amount_paid': p.amount_paid,
            'status': p.status,
            'description': p.description,
            'payment_date': p.payment_date,
            'reference': p.reference
        })
