"""
Print mapped columns on Payment.__table__ to verify model mapping.
Usage: python scripts/print_payment_columns.py
"""
import os
import sys
from dotenv import load_dotenv

# Ensure project root on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

load_dotenv()

try:
    from models.register_pupils import Payment
    cols = [c.name for c in Payment.__table__.columns]
    print("Mapped Payment table columns:")
    for c in cols:
        print("-", c)
except Exception as e:
    print("Error importing Payment model:", e)
    raise
