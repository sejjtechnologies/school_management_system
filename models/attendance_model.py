from models.user_models import db
from datetime import datetime


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=True)
    stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(32), nullable=False)  # present|absent|late|leave
    reason = db.Column(db.Text, nullable=True)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('pupil_id', 'date', name='u_pupil_date'),
    )

    def __repr__(self):
        return f"<Attendance pupil={self.pupil_id} date={self.date} status={self.status}>"
