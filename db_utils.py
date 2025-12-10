#!/usr/bin/env python
"""
Direct database operations using Neon credentials from .env
"""

import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse
from functools import wraps

# Load environment variables
load_dotenv()

def get_db_connection():
    """Parse DATABASE_URL and return psycopg2 connection"""
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        raise ValueError("DATABASE_URL not found in .env file")
    
    # Parse the connection string
    parsed = urlparse(database_url)
    
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password,
        sslmode='require'
    )
    
    return conn

def safe_db_operation(operation_name="DB Operation"):
    """
    Decorator for SQLAlchemy database operations to handle transaction rollbacks.
    Ensures that if a transaction is aborted, it's properly rolled back.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from models.user_models import db
            from sqlalchemy.exc import InternalError
            
            try:
                result = func(*args, **kwargs)
                return result
            except InternalError as e:
                if "InFailedSqlTransaction" in str(e):
                    print(f"[{operation_name}] Transaction aborted, rolling back...")
                    try:
                        db.session.rollback()
                    except Exception as rollback_error:
                        print(f"[{operation_name}] Rollback failed: {str(rollback_error)}")
                raise
            except Exception as e:
                print(f"[{operation_name}] Error: {str(e)}")
                try:
                    db.session.rollback()
                except Exception:
                    pass
                raise
        return wrapper
    return decorator

def execute_sql(sql_query, fetch=False):
    """Execute SQL query directly to Neon database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print(f"🔄 Executing SQL...")
        cursor.execute(sql_query)
        
        if fetch:
            results = cursor.fetchall()
            conn.commit()
            cursor.close()
            conn.close()
            return results
        else:
            conn.commit()
            cursor.close()
            conn.close()
            print("✅ SQL executed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def recreate_timetable_table():
    """Drop and recreate timetable_slots with new constraint"""
    
    drop_sql = "DROP TABLE IF EXISTS timetable_slots CASCADE;"
    
    create_sql = """
    CREATE TABLE timetable_slots (
        id SERIAL PRIMARY KEY,
        teacher_id INTEGER NOT NULL REFERENCES users(id),
        class_id INTEGER NOT NULL REFERENCES classes(id),
        stream_id INTEGER NOT NULL REFERENCES streams(id),
        subject_id INTEGER NOT NULL REFERENCES subjects(id),
        day_of_week VARCHAR(20) NOT NULL,
        start_time VARCHAR(5) NOT NULL,
        end_time VARCHAR(5) NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT unique_teacher_stream_slot UNIQUE(teacher_id, stream_id, day_of_week, start_time),
        CONSTRAINT unique_class_slot UNIQUE(class_id, stream_id, day_of_week, start_time)
    );
    """
    
    print("📊 Recreating timetable_slots table with new constraints...")
    print("\n1️⃣  Dropping old table...")
    execute_sql(drop_sql)
    
    print("\n2️⃣  Creating new table with updated constraints...")
    execute_sql(create_sql)
    
    print("\n✅ SUCCESS!")
    print("\n📋 New Constraints:")
    print("   • unique_teacher_stream_slot: (teacher_id, stream_id, day_of_week, start_time)")
    print("     → Teachers can teach multiple streams at the same time")
    print("   • unique_class_slot: (class_id, stream_id, day_of_week, start_time)")
    print("     → Each stream can only have one teacher at a time")

if __name__ == "__main__":
    print("🚀 Direct Neon Database Connection Utility\n")
    recreate_timetable_table()
