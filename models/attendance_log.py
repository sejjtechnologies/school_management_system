from models.user_models import db
from datetime import datetime


class AttendanceLog(db.Model):
    __tablename__ = 'attendance_log'

    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=True)
    pupil_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    old_status = db.Column(db.String(32), nullable=True)
    new_status = db.Column(db.String(32), nullable=True)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    note = db.Column(db.Text, nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AttendanceLog pupil={self.pupil_id} date={self.date} {self.old_status}->{self.new_status}>"
