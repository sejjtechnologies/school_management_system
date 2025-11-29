import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from datetime import datetime

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

# -----------------------------
# Flask app and DB setup
# -----------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------------
# Pupil model with auto-updating balance
# -----------------------------
class Pupil(db.Model):
    __tablename__ = 'pupils'

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)

    total_paid = db.Column(db.Float, default=0.0)
    balance = db.Column(db.Float, default=0.0)

    payments = db.relationship("Payment", back_populates="pupil", lazy=True, cascade="all, delete-orphan")

    def update_balance(self):
        """Recalculate total_paid and balance."""
        self.total_paid = sum(payment.amount_paid for payment in self.payments)
        self.balance = sum(payment.fee.amount for payment in self.payments if payment.fee) - self.total_paid

# -----------------------------
# Fee table
# -----------------------------
class Fee(db.Model):
    __tablename__ = 'fees'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    term = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship("Payment", back_populates="fee", lazy=True, cascade="all, delete-orphan")

# -----------------------------
# Payment table
# -----------------------------
class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    fee_id = db.Column(db.Integer, db.ForeignKey('fees.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50), nullable=True)

    pupil = db.relationship("Pupil", back_populates="payments")
    fee = db.relationship("Fee", back_populates="payments")

# -----------------------------
# SQLAlchemy event to auto-update balances
# -----------------------------
@event.listens_for(Payment, 'after_insert')
@event.listens_for(Payment, 'after_update')
@event.listens_for(Payment, 'after_delete')
def update_pupil_balance(mapper, connection, target):
    pupil = target.pupil
    if pupil:
        pupil.update_balance()
        db.session.add(pupil)
        db.session.commit()

# -----------------------------
# Initialize tables and update existing balances
# -----------------------------
if __name__ == "__main__":
    try:
        with app.app_context():
            db.create_all()  # create tables if not exist

            # Initialize balances for existing pupils
            pupils = Pupil.query.all()
            for pupil in pupils:
                pupil.update_balance()
            db.session.commit()

        print("✅ Tables created/updated successfully and balances auto-update on payments!")
    except Exception as e:
        print("❌ Error creating tables or updating balances:", e)
