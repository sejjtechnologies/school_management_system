from models.user_models import db
from datetime import datetime

class SystemSettings(db.Model):
    """
    Stores global system configuration for Backup & Maintenance.
    Only one record should exist in the database.
    """
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    
    # Backup & Maintenance Settings
    backup_schedule = db.Column(db.String(50), default='weekly')  # 'daily', 'weekly', 'monthly'
    backup_location = db.Column(db.String(255), default='/backups')  # Path where backups are stored
    last_backup_time = db.Column(db.DateTime, nullable=True)  # When was the last backup performed
    next_scheduled_backup = db.Column(db.DateTime, nullable=True)  # When is the next backup scheduled
    
    # Maintenance Mode
    maintenance_mode = db.Column(db.Boolean, default=False)  # True = system is in maintenance mode
    maintenance_message = db.Column(db.Text, default='System is under maintenance. Please try again later.')
    
    # Auto-backup enabled/disabled
    auto_backup_enabled = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Track who made changes

    def __repr__(self):
        return f'<SystemSettings id={self.id} schedule={self.backup_schedule} maintenance_mode={self.maintenance_mode}>'

    @staticmethod
    def get_settings():
        """Fetch the single system settings record; create default if none exists."""
        settings = SystemSettings.query.first()
        if not settings:
            settings = SystemSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
