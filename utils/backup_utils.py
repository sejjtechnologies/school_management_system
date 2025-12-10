"""
Database backup utility module.
Handles creation, management, and restoration of database backups.
"""
import os
import subprocess
import gzip
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")


def ensure_backup_directory():
    """Create backup directory if it doesn't exist."""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    return BACKUP_DIR


def parse_database_url(db_url):
    """
    Parse PostgreSQL connection string and return connection parameters.
    Supports both standard and Neon PostgreSQL URLs.
    """
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(db_url)

    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password,
    }


def create_backup(description="manual", progress_callback=None):
    """
    Create a backup of the database.
    
    Args:
        description (str): Backup type ('manual', 'scheduled', 'daily', 'weekly', 'monthly')
    
    Returns:
        dict: Status with keys:
            - success (bool): Whether backup was successful
            - backup_file (str): Path to backup file
            - message (str): Status message
            - timestamp (datetime): When backup was created
    """
    try:
        ensure_backup_directory()

        if not DATABASE_URL:
            return {
                'success': False,
                'backup_file': None,
                'message': 'DATABASE_URL not configured',
                'timestamp': datetime.now()
            }

        # Parse database URL
        db_config = parse_database_url(DATABASE_URL)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}_{description}.sql"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        # Set environment variables for pg_dump
        env = os.environ.copy()
        if db_config['password']:
            env['PGPASSWORD'] = db_config['password']

        # Construct pg_dump command
        pg_dump_cmd = [
            'pg_dump',
            '-h', db_config['host'],
            '-p', str(db_config['port']),
            '-U', db_config['user'],
            '-d', db_config['database'],
            '--verbose',
            '--no-password'
        ]

        # Add SSL mode for Neon connections
        if 'neon' in db_config['host'].lower():
            pg_dump_cmd.extend(['--no-password'])
            env['PGSSLMODE'] = 'require'

        # Execute pg_dump and save to file
        if progress_callback:
            try:
                progress_callback(10, 'Starting pg_dump')
            except Exception:
                pass
        with open(backup_path, 'w') as backup_file:
            result = subprocess.run(
                pg_dump_cmd,
                stdout=backup_file,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                timeout=300  # 5 minute timeout
            )
        if progress_callback:
            try:
                # pg_dump finished (success or failure) - mark progress
                progress_callback(60, 'pg_dump finished')
            except Exception:
                pass
        if result.returncode != 0:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return {
                'success': False,
                'backup_file': None,
                'message': f'pg_dump error: {result.stderr}',
                'timestamp': datetime.now()
            }

        # Compress the backup
        if progress_callback:
            try:
                progress_callback(70, 'Starting compression')
            except Exception:
                pass
        compressed_path = f"{backup_path}.gz"
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        if progress_callback:
            try:
                progress_callback(95, 'Compression complete')
            except Exception:
                pass
        # Remove uncompressed backup
        os.remove(backup_path)

        # Get file size
        file_size = os.path.getsize(compressed_path)
        file_size_mb = file_size / (1024 * 1024)

        if progress_callback:
            try:
                progress_callback(100, 'Backup complete')
            except Exception:
                pass

        return {
            'success': True,
            'backup_file': compressed_path,
            'filename': f"{backup_filename}.gz",
            'file_size': file_size,
            'file_size_mb': f"{file_size_mb:.2f}",
            'message': f'Backup created successfully ({file_size_mb:.2f} MB)',
            'timestamp': datetime.now()
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'backup_file': None,
            'message': 'Backup timeout (>5 minutes)',
            'timestamp': datetime.now()
        }
    except FileNotFoundError:
        return {
            'success': False,
            'backup_file': None,
            'message': 'pg_dump not found. Please install PostgreSQL client tools.',
            'timestamp': datetime.now()
        }
    except Exception as e:
        return {
            'success': False,
            'backup_file': None,
            'message': f'Backup error: {str(e)}',
            'timestamp': datetime.now()
        }


def list_backups():
    """
    List all available backups.
    
    Returns:
        list: List of backup file info dicts with:
            - filename (str): Backup filename
            - path (str): Full path to backup
            - size (int): File size in bytes
            - size_mb (str): File size in MB
            - created (datetime): When backup was created
    """
    try:
        ensure_backup_directory()

        backups = []
        for filename in sorted(os.listdir(BACKUP_DIR), reverse=True):
            filepath = os.path.join(BACKUP_DIR, filename)
            if os.path.isfile(filepath) and filename.endswith('.gz'):
                stat = os.stat(filepath)
                size_mb = stat.st_size / (1024 * 1024)

                backups.append({
                    'filename': filename,
                    'path': filepath,
                    'size': stat.st_size,
                    'size_mb': f"{size_mb:.2f}",
                    'created': datetime.fromtimestamp(stat.st_mtime)
                })

        return backups
    except Exception as e:
        print(f"Error listing backups: {e}")
        return []


def get_latest_backup():
    """
    Get the most recent backup.
    
    Returns:
        dict: Backup info or None if no backups exist
    """
    backups = list_backups()
    return backups[0] if backups else None


def delete_backup(backup_filename):
    """
    Delete a specific backup file.
    
    Args:
        backup_filename (str): Filename of backup to delete
    
    Returns:
        dict: Status with success (bool) and message (str)
    """
    try:
        # Validate filename to prevent directory traversal
        if '..' in backup_filename or '/' in backup_filename or '\\' in backup_filename:
            return {'success': False, 'message': 'Invalid backup filename'}

        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        print(f"[BACKUP_UTILS] Delete attempt - BACKUP_DIR: {BACKUP_DIR}")
        print(f"[BACKUP_UTILS] Delete attempt - filename: {backup_filename}")
        print(f"[BACKUP_UTILS] Delete attempt - full path: {backup_path}")
        print(f"[BACKUP_UTILS] Delete attempt - exists: {os.path.exists(backup_path)}")

        if not os.path.exists(backup_path):
            return {'success': False, 'message': 'Backup file not found'}

        os.remove(backup_path)
        print(f"[BACKUP_UTILS] Delete success - file removed")
        return {'success': True, 'message': f'Backup {backup_filename} deleted'}
    except Exception as e:
        print(f"[BACKUP_UTILS] Delete error: {str(e)}")
        return {'success': False, 'message': f'Error deleting backup: {str(e)}'}


def cleanup_old_backups(keep_count=10):
    """
    Delete old backups keeping only the most recent ones.
    
    Args:
        keep_count (int): Number of recent backups to keep
    
    Returns:
        dict: Status with count removed
    """
    try:
        backups = list_backups()
        to_delete = backups[keep_count:]

        deleted_count = 0
        for backup in to_delete:
            try:
                os.remove(backup['path'])
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {backup['filename']}: {e}")

        return {'success': True, 'deleted_count': deleted_count}
    except Exception as e:
        return {'success': False, 'message': f'Cleanup error: {str(e)}'}
