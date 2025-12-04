from models.user_models import db
from datetime import datetime

# ============================================================
# 1. PUPIL MODEL
# ============================================================
class Pupil(db.Model):
    __tablename__ = 'pupils'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.String(50), unique=True, nullable=True)
    admission_number = db.Column(db.String(50), unique=True, nullable=False)
    admission_date = db.Column(db.Date, nullable=False)

    # Personal info
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    nationality = db.Column(db.String(50), nullable=False)
    place_of_birth = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(200), nullable=True)

    # Contacts
    home_address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    emergency_contact = db.Column(db.String(100), nullable=False)
    emergency_phone = db.Column(db.String(20), nullable=False)

    # Guardian
    guardian_name = db.Column(db.String(100), nullable=False)
    guardian_relationship = db.Column(db.String(50), nullable=False)
    guardian_occupation = db.Column(db.String(100), nullable=True)
    guardian_phone = db.Column(db.String(20), nullable=False)
    guardian_address = db.Column(db.String(200), nullable=True)

    # Academic
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'), nullable=True)
    previous_school = db.Column(db.String(100), nullable=True)
    roll_number = db.Column(db.String(50), nullable=True)

    enrollment_status = db.Column(db.String(20), nullable=False)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    class_ = db.relationship("Class", backref="pupils")
    stream = db.relationship("Stream", backref="pupils")
    payments = db.relationship("Payment", back_populates="pupil", cascade="all, delete-orphan")

    # Exam tracking
    marks = db.relationship("Mark", back_populates="pupil", cascade="all, delete-orphan")
    reports = db.relationship("Report", back_populates="pupil", cascade="all, delete-orphan")

    # -------------------------
    # Fee calculations
    # -------------------------
    @property
    def class_fees(self):
        """Returns list of required fee items for this pupil's class."""
        return self.class_.fee_items if self.class_ else []

    @property
    def total_required(self):
        return sum(item.amount for item in self.class_fees)

    @property
    def total_paid(self):
        return sum(p.amount_paid for p in self.payments)

    @property
    def balance(self):
        return self.total_required - self.total_paid

    def __repr__(self):
        return f"<Pupil {self.first_name} {self.last_name}>"


# ============================================================
# 2. CLASS FEES STRUCTURE
# ============================================================
class ClassFeeStructure(db.Model):
    __tablename__ = "class_fees_structure"

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)

    class_ = db.relationship("Class", backref="fee_items")

    def __repr__(self):
        return f"<FeeItem {self.item_name} - {self.amount}>"


# ============================================================
# 3. PAYMENTS TABLE (UPDATED TO MATCH NEON)
# ============================================================
class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)

    # NEW: Matches Neon DB
    fee_id = db.Column(db.Integer, db.ForeignKey('class_fees_structure.id'), nullable=False)

    amount_paid = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50), nullable=True)
    reference = db.Column(db.String(100), nullable=True)
    
    # Academic period tracking
    year = db.Column(db.Integer, nullable=True)
    term = db.Column(db.String(20), nullable=True)

    # Relationships
    pupil = db.relationship("Pupil", back_populates="payments")
    fee_item = db.relationship("ClassFeeStructure")

    def __repr__(self):
        return f"<Payment {self.amount_paid} for Pupil {self.pupil_id}, Fee {self.fee_id}>"
