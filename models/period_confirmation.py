from models.user_models import db
from datetime import datetime


class PeriodConfirmation(db.Model):
    __tablename__ = 'period_confirmations'

    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    period_type = db.Column(db.String(16), nullable=False)  # 'week' or 'month'
    days = db.Column(db.Integer, nullable=False, default=6)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('class_id', 'start_date', 'period_type', name='u_class_start_period'),
    )

    def __repr__(self):
        return f"<PeriodConfirmation class={self.class_id} start={self.start_date} type={self.period_type} by={self.confirmed_by}>"
