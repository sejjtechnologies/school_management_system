from models.user_models import db  # ✅ Use shared db instance
from datetime import datetime

class Pupil(db.Model):
    __tablename__ = 'pupils'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.String(50), unique=True, nullable=True)
    admission_number = db.Column(db.String(50), unique=True, nullable=False)
    admission_date = db.Column(db.Date, nullable=False)

    # Student personal info
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    nationality = db.Column(db.String(50), nullable=False)
    place_of_birth = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(200), nullable=True)

    # Contact info
    home_address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    emergency_contact = db.Column(db.String(100), nullable=False)
    emergency_phone = db.Column(db.String(20), nullable=False)

    # Guardian info
    guardian_name = db.Column(db.String(100), nullable=False)
    guardian_relationship = db.Column(db.String(50), nullable=False)
    guardian_occupation = db.Column(db.String(100), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=False)
    guardian_address = db.Column(db.String(200), nullable=True)

    # Academic info
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'), nullable=True)
    previous_school = db.Column(db.String(100), nullable=True)
    roll_number = db.Column(db.String(50), nullable=True)

    # System fields
    enrollment_status = db.Column(db.String(20), nullable=False)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ Relationships
    class_ = db.relationship('Class', backref='pupils', lazy=True)
    stream = db.relationship('Stream', backref='pupils', lazy=True)

    # ✅ Relationships to marks and reports
    marks = db.relationship("Mark", back_populates="pupil", lazy=True, cascade="all, delete-orphan")
    reports = db.relationship("Report", back_populates="pupil", lazy=True, cascade="all, delete-orphan")

    # ✅ Relationship to payments
    payments = db.relationship("Payment", back_populates="pupil", lazy=True, cascade="all, delete-orphan")

    # -----------------------------
    # Convenience properties
    # -----------------------------
    @property
    def total_paid(self):
        return sum(payment.amount_paid for payment in self.payments)

    @property
    def total_fees(self):
        return sum(payment.fee.amount for payment in self.payments if payment.fee)

    @property
    def balance(self):
        return self.total_fees - self.total_paid

    def __repr__(self):
        return f"<Pupil {self.first_name} {self.last_name} (Admission {self.admission_number})>"

# -----------------------------
# Fees Table
# -----------------------------
class Fee(db.Model):
    __tablename__ = 'fees'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    term = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)  # <-- Added
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to payments
    payments = db.relationship("Payment", back_populates="fee", lazy=True, cascade="all, delete-orphan")
    class_ = db.relationship('Class', backref='fees', lazy=True)  # Optional convenience

    def __repr__(self):
        return f"<Fee {self.name} - UGX {self.amount:,.0f} - Class ID {self.class_id}>"

# -----------------------------
# Payments Table
# -----------------------------
class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    fee_id = db.Column(db.Integer, db.ForeignKey('fees.id'), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50), nullable=True)

    # Relationships
    pupil = db.relationship("Pupil", back_populates="payments")
    fee = db.relationship("Fee", back_populates="payments")

    def __repr__(self):
        return f"<Payment UGX {self.amount_paid:,.0f} for Pupil {self.pupil_id} - Fee {self.fee_id}>"
