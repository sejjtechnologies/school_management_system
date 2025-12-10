#!/usr/bin/env python
"""Apply system_settings table migration directly."""
import os
from dotenv import load_dotenv
from models.user_models import db
from models.system_settings import SystemSettings
from app import app

# Load environment variables
load_dotenv()

with app.app_context():
    # Create all tables defined in models
    try:
        # Create the system_settings table if it doesn't exist
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Create default SystemSettings record if none exists
        settings = SystemSettings.query.first()
        if not settings:
            settings = SystemSettings()
            db.session.add(settings)
            db.session.commit()
            print("✅ Default SystemSettings record created!")
        else:
            print("✅ SystemSettings record already exists!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
