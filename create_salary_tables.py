#!/usr/bin/env python3
"""
Direct Neon Database Setup Script for Salary Management Tables

This script:
1. Loads DATABASE_URL from .env file
2. Connects directly to Neon PostgreSQL database
3. Creates the new salary tables (role_salaries, salary_payments)
4. Adds salary_amount column to users table if not present

Usage:
  python create_salary_tables.py
  
Requirements:
  - .env file in project root with DATABASE_URL
  - psycopg2 or psycopg[binary] installed
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_env_file(env_path='.env'):
    """Load environment variables from .env file."""
    env_file = Path(env_path)
    if not env_file.exists():
        raise FileNotFoundError(f"❌ .env file not found at {env_path}")
    
    load_dotenv(env_file)
    logger.info(f"✓ Loaded .env from {env_path}")


def get_database_url():
    """Retrieve DATABASE_URL from environment."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("❌ DATABASE_URL not set in environment. Check .env file.")
    
    logger.info(f"✓ DATABASE_URL found (length: {len(db_url)})")
    return db_url


def connect_to_database(db_url):
    """Connect to Neon PostgreSQL database."""
    try:
        conn = psycopg2.connect(db_url)
        logger.info("✓ Connected to Neon database successfully")
        return conn
    except psycopg2.Error as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        raise


def table_exists(cursor, table_name):
    """Check if a table exists in the database."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = %s
        )
    """, (table_name,))
    return cursor.fetchone()[0]


def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        )
    """, (table_name, column_name))
    return cursor.fetchone()[0]


def create_role_salaries_table(cursor):
    """Create the role_salaries table."""
    if table_exists(cursor, 'role_salaries'):
        logger.warning("⚠ Table 'role_salaries' already exists. Skipping creation.")
        return
    
    sql = """
    CREATE TABLE IF NOT EXISTS role_salaries (
        id SERIAL PRIMARY KEY,
        role_id INTEGER NOT NULL UNIQUE REFERENCES roles(id) ON DELETE CASCADE,
        amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
        min_amount NUMERIC(12, 2),
        max_amount NUMERIC(12, 2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    cursor.execute(sql)
    logger.info("✓ Created table 'role_salaries'")


def create_salary_payments_table(cursor):
    """Create the salary_payments table."""
    if table_exists(cursor, 'salary_payments'):
        logger.warning("⚠ Table 'salary_payments' already exists. Skipping creation.")
        return
    
    sql = """
    CREATE TABLE IF NOT EXISTS salary_payments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL,
        amount NUMERIC(12, 2) NOT NULL,
        paid_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        period_month INTEGER,
        period_year INTEGER,
        term VARCHAR(20),
        year INTEGER,
        status VARCHAR(20) NOT NULL DEFAULT 'paid',
        reference VARCHAR(100),
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX idx_salary_payments_user_id ON salary_payments(user_id);
    CREATE INDEX idx_salary_payments_role_id ON salary_payments(role_id);
    CREATE INDEX idx_salary_payments_status ON salary_payments(status);
    CREATE INDEX idx_salary_payments_period ON salary_payments(period_year, period_month);
    """
    cursor.execute(sql)
    logger.info("✓ Created table 'salary_payments' with indexes")


def add_salary_amount_to_users(cursor):
    """Add salary_amount column to users table if not present."""
    if not column_exists(cursor, 'users', 'salary_amount'):
        sql = """
        ALTER TABLE users ADD COLUMN salary_amount NUMERIC(12, 2);
        """
        cursor.execute(sql)
        logger.info("✓ Added 'salary_amount' column to 'users' table")
    else:
        logger.warning("⚠ Column 'salary_amount' already exists in 'users' table. Skipping.")


def main():
    """Main execution flow."""
    try:
        # Load environment variables
        load_env_file('.env')
        
        # Get database URL
        db_url = get_database_url()
        
        # Connect to database
        conn = connect_to_database(db_url)
        cursor = conn.cursor()
        
        logger.info("\n" + "="*60)
        logger.info("Starting database setup for salary management")
        logger.info("="*60 + "\n")
        
        # Create tables
        logger.info("Creating/Verifying tables...")
        create_role_salaries_table(cursor)
        create_salary_payments_table(cursor)
        add_salary_amount_to_users(cursor)
        
        # Commit changes
        conn.commit()
        logger.info("\n✓ All changes committed to database")
        
        # Verify tables were created
        logger.info("\nVerifying table creation...")
        if table_exists(cursor, 'role_salaries'):
            logger.info("✓ role_salaries table exists")
        if table_exists(cursor, 'salary_payments'):
            logger.info("✓ salary_payments table exists")
        if column_exists(cursor, 'users', 'salary_amount'):
            logger.info("✓ salary_amount column exists in users table")
        
        # Close connection
        cursor.close()
        conn.close()
        
        logger.info("\n" + "="*60)
        logger.info("✓ Database setup completed successfully!")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("1. Verify your Flask app imports the new models:")
        logger.info("   - from models.salary_models import RoleSalary, SalaryPayment")
        logger.info("2. Create bursar routes for managing staff salaries")
        logger.info("3. Create a template for the 'Manage Staff Salaries' page")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"❌ File error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    except psycopg2.Error as e:
        logger.error(f"❌ Database error: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
