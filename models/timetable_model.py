from models.user_models import db, User
from models.class_model import Class
from models.stream_model import Stream
from models.marks_model import Subject
from datetime import datetime


class TimeTableSlot(db.Model):
    """
    Represents a teaching slot in the timetable.
    Each slot assigns a teacher to teach a specific subject
    in a specific class/stream at a specific time on a specific day.
    """
    __tablename__ = "timetable_slots"

    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey("streams.id"), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)

    # Day & Time (24-hour format)
    day_of_week = db.Column(db.String(20), nullable=False)  # Monday, Tuesday, ..., Saturday
    start_time = db.Column(db.String(5), nullable=False)    # HH:MM format (e.g., "08:00")
    end_time = db.Column(db.String(5), nullable=False)      # HH:MM format (e.g., "09:00")

    # Metadata
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teacher = db.relationship("User", backref="timetable_slots", lazy=True)
    class_ = db.relationship("Class", backref="timetable_slots", lazy=True)
    stream = db.relationship("Stream", backref="timetable_slots", lazy=True)
    subject = db.relationship("Subject", backref="timetable_slots", lazy=True)

    # Unique constraint: A teacher cannot teach the same class at the same time
    __table_args__ = (
        db.UniqueConstraint('teacher_id', 'day_of_week', 'start_time', name='unique_teacher_slot'),
        db.UniqueConstraint('class_id', 'stream_id', 'day_of_week', 'start_time', name='unique_class_slot'),
    )

    def __repr__(self):
        return f"<TimeTableSlot Teacher={self.teacher_id} Class={self.class_id} {self.day_of_week} {self.start_time}-{self.end_time}>"

    @staticmethod
    def get_time_slots():
        """Returns available time slots for the day (8AM to 5PM, hourly)"""
        slots = []
        hours = range(8, 17)  # 8 AM to 5 PM (17:00)
        for hour in hours:
            start = f"{hour:02d}:00"
            end = f"{hour+1:02d}:00"
            slots.append((start, end))
        return slots

    @staticmethod
    def get_days():
        """Returns available days for timetable"""
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
