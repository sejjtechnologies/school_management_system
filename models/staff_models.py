from datetime import datetime
from models.user_models import db


class StaffAttendance(db.Model):
    __tablename__ = 'staff_attendance'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # present|absent|leave
    term = db.Column(db.String(50), nullable=True)
    year = db.Column(db.Integer, nullable=True, index=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('staff_id', 'date', name='u_staff_date'),
    )

    def __repr__(self):
        return f"<StaffAttendance staff={self.staff_id} date={self.date} status={self.status}>"


class SalaryHistory(db.Model):
    __tablename__ = 'salary_history'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    old_salary = db.Column(db.Numeric(12, 2), nullable=False)
    new_salary = db.Column(db.Numeric(12, 2), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SalaryHistory staff={self.staff_id} {self.old_salary}->{self.new_salary} by={self.changed_by}>"


class StaffProfile(db.Model):
    __tablename__ = 'staff_profiles'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(100), nullable=True)
    tax_id = db.Column(db.String(100), nullable=True)
    pay_grade = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<StaffProfile staff={self.staff_id} bank={self.bank_name}>"
