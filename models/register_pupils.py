from models.user_models import db  # ✅ Use shared db instance
from datetime import datetime

class Pupil(db.Model):
    __tablename__ = 'pupils'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.String(50), unique=True, nullable=True)  # optional unique identifier
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