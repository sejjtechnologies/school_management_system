#!/usr/bin/env python
"""Create system_settings table directly using psycopg2."""
import os
from dotenv import load_dotenv
import psycopg2
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable not set!")
    exit(1)

print(f"Connecting to database...")

try:
    # Parse the database URL
    parsed = urlparse(DATABASE_URL)
    
    # Create connection
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password,
        sslmode='require'
    )
    
    cursor = conn.cursor()
    
    # Create the system_settings table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS system_settings (
        id SERIAL PRIMARY KEY,
        backup_schedule VARCHAR(50) DEFAULT 'weekly',
        backup_location VARCHAR(255) DEFAULT '/backups',
        last_backup_time TIMESTAMP NULL,
        next_scheduled_backup TIMESTAMP NULL,
        maintenance_mode BOOLEAN DEFAULT FALSE,
        maintenance_message TEXT DEFAULT 'System is under maintenance. Please try again later.',
        auto_backup_enabled BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_by_user_id INTEGER REFERENCES users(id),
        UNIQUE(id)
    );
    """
    
    cursor.execute(create_table_sql)
    
    # Insert default record if table is empty
    cursor.execute("SELECT COUNT(*) FROM system_settings;")
    count = cursor.fetchone()[0]
    
    if count == 0:
        insert_sql = """
        INSERT INTO system_settings (backup_schedule, maintenance_mode, auto_backup_enabled)
        VALUES ('weekly', FALSE, TRUE);
        """
        cursor.execute(insert_sql)
        print("✅ Default SystemSettings record created!")
    else:
        print("✅ SystemSettings record already exists!")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("✅ Database tables created successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
