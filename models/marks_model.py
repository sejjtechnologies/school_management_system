from models.user_models import db   # ✅ Use the shared db instance
from models.register_pupils import Pupil   # ✅ Import Pupil explicitly


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f"<Subject {self.name}>"


class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)

    # ✅ Exam type: e.g. "Midterm", "End Term"
    name = db.Column(db.String(100), nullable=False)

    # ✅ Term stored as integer (1, 2, 3)
    term = db.Column(db.Integer, nullable=False)

    # ✅ Academic year (e.g. 2025)
    year = db.Column(db.Integer, nullable=False)

    # Relationships
    marks = db.relationship("Mark", back_populates="exam", cascade="all, delete-orphan")
    reports = db.relationship("Report", back_populates="exam", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exam {self.name} Term {self.term} Year {self.year}>"


class Mark(db.Model):
    __tablename__ = 'marks'
    id = db.Column(db.Integer, primary_key=True)

    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)

    score = db.Column(db.Float, nullable=False)

    # ✅ Relationships
    pupil = db.relationship("Pupil", back_populates="marks")
    subject = db.relationship("Subject", backref="marks")
    exam = db.relationship("Exam", back_populates="marks")

    def __repr__(self):
        return f"<Mark Pupil {self.pupil_id} Subject {self.subject_id} Exam {self.exam_id} Score {self.score}>"


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)

    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)

    total_score = db.Column(db.Float, nullable=False)
    average_score = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    remarks = db.Column(db.String(255))

    # ✅ New columns for positions
    stream_position = db.Column(db.Integer)   # Rank within stream
    class_position = db.Column(db.Integer)    # Rank within class

    # ✅ New column for overall performance comment
    general_remark = db.Column(db.String(255))

    # ✅ Relationships
    pupil = db.relationship("Pupil", back_populates="reports")
    exam = db.relationship("Exam", back_populates="reports")

    def __repr__(self):
        return (
            f"<Report Pupil {self.pupil_id} Exam {self.exam_id} "
            f"Grade {self.grade} StreamPos {self.stream_position} "
            f"ClassPos {self.class_position} GeneralRemark {self.general_remark}>"
        )