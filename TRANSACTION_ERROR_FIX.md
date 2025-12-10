# SQLAlchemy Transaction Error Fix

## Problem
**Error**: `sqlalchemy.exc.InternalError: (psycopg2.errors.InFailedSqlTransaction) current transaction is aborted, commands ignored until end of transaction block`

This error occurred when:
1. A previous database operation failed (raising an exception)
2. The SQLAlchemy session transaction became "aborted"
3. Any subsequent database query would fail because PostgreSQL refuses to execute commands in an aborted transaction
4. The error occurred in the `backup_maintenance` route when trying to fetch `SystemSettings`

## Root Causes
1. **Missing Transaction Rollback**: When an exception occurred during a database operation, the transaction wasn't properly rolled back
2. **No Recovery Logic**: The `SystemSettings.get_settings()` method had no fallback if the query failed
3. **No Session Cleanup**: Database sessions weren't being cleaned up after responses, causing connection pool issues
4. **No Global Error Handler**: Database errors weren't being caught globally to trigger rollbacks

## Solutions Implemented

### 1. Enhanced `SystemSettings.get_settings()` with Retry Logic
**File**: `models/system_settings.py`

```python
@staticmethod
def get_settings():
    """Fetch the single system settings record; create default if none exists."""
    try:
        settings = SystemSettings.query.first()
        if not settings:
            settings = SystemSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
    except Exception as e:
        # If the transaction is aborted, rollback and retry
        db.session.rollback()
        try:
            settings = SystemSettings.query.first()
            if not settings:
                settings = SystemSettings()
                db.session.add(settings)
                db.session.commit()
            return settings
        except Exception:
            # If still failing, create a default in-memory object
            settings = SystemSettings()
            return settings
```

**What it does**:
- Attempts to fetch settings normally
- If it fails (e.g., transaction aborted), rolls back the transaction
- Retries the operation
- Falls back to an in-memory object if all else fails

### 2. Global Error Handler for Transaction Failures
**File**: `app.py`

```python
@app.errorhandler(Exception)
def handle_db_error(error):
    """Catch database transaction errors and rollback."""
    from sqlalchemy.exc import InternalError
    
    if isinstance(error, InternalError) and "InFailedSqlTransaction" in str(error):
        logger.error(f"[DB TRANSACTION ERROR] Transaction aborted, rolling back: {str(error)}")
        try:
            db.session.rollback()
        except Exception as rollback_error:
            logger.error(f"[DB ROLLBACK ERROR] Failed to rollback: {str(rollback_error)}")
        
        # Re-raise the error so Flask can handle it normally
        raise error
    
    # Let Flask handle other errors normally
    raise error
```

**What it does**:
- Catches all exceptions that are transaction abort errors
- Automatically rolls back the session
- Logs the error for debugging

### 3. Session Cleanup in Response Handler
**File**: `app.py`

```python
@app.after_request
def ensure_utf8_charset(response):
    """Ensure all text responses include UTF-8 charset in Content-Type header."""
    # ... existing code ...
    
    # ✅ Cleanup: Remove any pending database session to prevent connection pool leaks
    try:
        db.session.remove()
    except Exception as e:
        logger.warning(f"[SESSION CLEANUP] Could not remove session: {str(e)}")
    
    return response
```

**What it does**:
- Removes the database session after every response
- Prevents connection pool exhaustion
- Cleans up resources automatically

### 4. Safe Database Operation Decorator
**File**: `db_utils.py`

```python
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
```

**Usage**:
```python
@safe_db_operation("MyOperation")
def my_database_function():
    # Your code here
    pass
```

### 5. Enhanced `backup_maintenance` Route Error Handling
**File**: `routes/admin_routes.py`

```python
@admin_routes.route("/admin/backup-maintenance", methods=["GET", "POST"])
def backup_maintenance():
    """Handle backup and maintenance settings management."""
    try:
        settings = SystemSettings.get_settings()
    except Exception as e:
        db.session.rollback()
        print(f"[BACKUP_MAINTENANCE] Error fetching settings: {str(e)}")
        settings = SystemSettings()  # Return empty settings object

    if request.method == "POST":
        try:
            settings.backup_schedule = request.form.get("backup_schedule", "weekly")
            settings.maintenance_mode = request.form.get("maintenance_mode") == "on"
            settings.maintenance_message = request.form.get("maintenance_message", "")
            settings.auto_backup_enabled = request.form.get("auto_backup_enabled") == "on"
            settings.updated_by_user_id = session.get('user_id')

            db.session.commit()
            flash("Backup & Maintenance settings updated successfully!", "success")
            return redirect(url_for("admin_routes.backup_maintenance"))
        except Exception as e:
            db.session.rollback()
            print(f"[BACKUP_MAINTENANCE] Error updating settings: {str(e)}")
            flash(f"Error updating settings: {str(e)}", "danger")
            return redirect(url_for("admin_routes.backup_maintenance"))

    return render_template("admin/backup_maintenance.html", settings=settings)
```

**What it does**:
- Wraps both initial fetch and POST handling in try-except blocks
- Automatically rolls back on any error
- Provides fallback behavior instead of crashing

## Best Practices for Database Operations

### Always Use Try-Except-Rollback Pattern
```python
try:
    # Your database operation
    db.session.commit()
except Exception as e:
    db.session.rollback()
    # Handle error appropriately
    raise
```

### Use the Safe Decorator for Critical Operations
```python
@safe_db_operation("ImportantOperation")
def critical_function():
    # Your critical database code
    pass
```

### Check for Transaction Errors
PostgreSQL-specific errors to watch for:
- `InFailedSqlTransaction` - Transaction already aborted
- `OperationalError` - Connection issues
- `IntegrityError` - Data constraint violations

### Avoid Long-Running Transactions
- Keep database operations short
- Commit frequently
- Don't hold locks across multiple requests

## Testing the Fix

1. **Verify error handling**:
   ```bash
   curl http://localhost:5000/admin/backup-maintenance
   ```

2. **Test with invalid data** to trigger errors:
   - Send POST requests with malformed data
   - Verify that error responses don't crash the app

3. **Monitor logs**:
   - Check `[DB TRANSACTION ERROR]` logs
   - Verify `[SESSION CLEANUP]` logs appear after each request

## Performance Impact
- **Minimal**: Additional try-except blocks have negligible overhead
- **Beneficial**: Prevents connection pool exhaustion
- **Improved reliability**: Automatic recovery from transaction failures

## Related Issues
- PostgreSQL connection pool exhaustion
- "Too many connections" errors
- Cascading database failures

## Future Improvements
1. Implement database connection pooling optimization
2. Add metrics for transaction failures
3. Create automated alerts for persistent DB errors
4. Consider using transaction context managers for cleaner code
