# models/marks_model.py

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ✅ Subjects table
class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)

    def __repr__(self):
        return f"<Subject {self.name}>"

# ✅ Exams table
class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)   # e.g. "Midterm", "Final"
    term = db.Column(db.String(50), nullable=False)    # e.g. "Term 1"
    year = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Exam {self.name} - {self.term} {self.year}>"

# ✅ Marks table
class Mark(db.Model):
    __tablename__ = 'marks'
    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # numeric mark

    # Relationships
    pupil = db.relationship('Pupil', backref='marks', lazy=True)
    subject = db.relationship('Subject', backref='marks', lazy=True)
    exam = db.relationship('Exam', backref='marks', lazy=True)

    def __repr__(self):
        return f"<Mark pupil={self.pupil_id} subject={self.subject_id} exam={self.exam_id} score={self.score}>"

# ✅ Reports table
class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    total_score = db.Column(db.Float, nullable=False)
    average_score = db.Column(db.Float, nullable=False)
    grade = db.Column(db.String(5), nullable=False)
    remarks = db.Column(db.String(255))

    # Relationships
    pupil = db.relationship('Pupil', backref='reports', lazy=True)
    exam = db.relationship('Exam', backref='reports', lazy=True)

    def __repr__(self):
        return f"<Report pupil={self.pupil_id} exam={self.exam_id} grade={self.grade}>"