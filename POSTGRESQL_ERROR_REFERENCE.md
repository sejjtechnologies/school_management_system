# PostgreSQL Transaction Error Reference

## Error: InFailedSqlTransaction ✅ FIXED

### Symptoms
```
sqlalchemy.exc.InternalError: (psycopg2.errors.InFailedSqlTransaction) 
current transaction is aborted, commands ignored until end of transaction block
```

### Root Cause
A previous SQL operation failed, leaving the transaction in an aborted state. PostgreSQL refuses to execute any further commands until the transaction is rolled back.

### Solution (ALREADY IMPLEMENTED)
```python
except Exception as e:
    db.session.rollback()  # ← Reset transaction state
    # Retry or handle error
```

### Status
✅ **FIXED** - Automatic rollback + retry in `SystemSettings.get_settings()`

---

## Error: too many connections

### Symptoms
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
too many connections for role "...role..."
```

### Root Cause
Database sessions are not being cleaned up after requests, exhausting the connection pool.

### Solution (ALREADY IMPLEMENTED)
```python
@app.after_request
def ensure_utf8_charset(response):
    db.session.remove()  # ← Clean up session after response
    return response
```

### Status
✅ **FIXED** - Automatic session removal in response handler

---

## Error: server closed the connection unexpectedly

### Symptoms
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
server closed the connection unexpectedly
```

### Root Cause
Connection timeout or network issue. The connection to the database server was dropped.

### Solution (ALREADY IMPLEMENTED)
```python
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,  # ← Check connection before using
    "pool_recycle": 1800,   # ← Recycle old connections
}
```

### Status
✅ **FIXED** - Connection validation enabled in app.py

---

## Error: IntegrityError

### Symptoms
```
sqlalchemy.exc.IntegrityError: 
(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint
```

### Root Cause
Attempting to insert or update data that violates a database constraint.

### Solution
Validate data before database operations:
```python
try:
    # Validate data
    if not is_valid(data):
        return jsonify({"error": "Invalid data"}), 400
    
    # Insert/update
    db.session.commit()
except IntegrityError as e:
    db.session.rollback()
    return jsonify({"error": "Data constraint violation"}), 400
```

### Status
✅ **HANDLED** - Error handling pattern available

---

## Error: Foreign Key Constraint Violation

### Symptoms
```
sqlalchemy.exc.IntegrityError: 
(psycopg2.errors.ForeignKeyViolation) insert or update on table ... violates foreign key constraint
```

### Root Cause
Attempting to create a relationship to a non-existent parent record.

### Solution
```python
try:
    # Check parent exists before creating child
    parent = ParentModel.query.get(parent_id)
    if not parent:
        return jsonify({"error": "Parent record not found"}), 404
    
    child = ChildModel(parent_id=parent_id)
    db.session.add(child)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise
```

### Status
✅ **HANDLED** - Error handling pattern available

---

## Error: Deadlock Detected

### Symptoms
```
sqlalchemy.exc.OperationalError: 
(psycopg2.errors.DeadlockDetected) Deadlock detected
```

### Root Cause
Two operations trying to lock the same resources in opposite orders.

### Solution
```python
@safe_db_operation("CriticalOperation")
def perform_operation():
    # Your code here
    db.session.commit()
```

The decorator automatically handles retries for transient errors.

### Status
✅ **HANDLED** - Safe operation decorator available for retries

---

## Error: Serialization Failure

### Symptoms
```
sqlalchemy.exc.OperationalError: 
(psycopg2.errors.SerializationFailure) could not serialize access due to concurrent update
```

### Root Cause
Concurrent operations reading/writing the same data.

### Solution
Implement optimistic locking or use proper isolation levels:
```python
# Read current value
record = Model.query.get(id)
version = record.version

# Update with version check
record.field = new_value
db.session.commit()

# Handle version mismatch if needed
```

### Status
⚠️ **AVAILABLE** - Use safe operation decorator for retries

---

## Error: Statement Timeout

### Symptoms
```
sqlalchemy.exc.OperationalError: 
(psycopg2.errors.QueryCanceled) canceling statement due to statement timeout
```

### Root Cause
Query takes too long to execute.

### Solution
1. **Optimize the query** - Add indexes, refactor joins
2. **Increase timeout** - Only as last resort
3. **Break into smaller operations** - Process in batches

```python
# BAD: Slow query
results = VeryLargeTable.query.all()

# GOOD: Paginated query
page = 1
while True:
    results = VeryLargeTable.query.paginate(page=page, per_page=1000)
    # Process results
    if not results.has_next:
        break
    page += 1
```

### Status
ℹ️ **REQUIRES** - Query optimization (not automatic)

---

## Error: Prepared Statement Limit Exceeded

### Symptoms
```
sqlalchemy.exc.OperationalError: 
(psycopg2.errors.ObjectInUseByPreparedStatement) ...
```

### Root Cause
Too many prepared statements cached, especially with dynamic SQL.

### Solution
```python
# BAD: Dynamic SQL without parameterization
query = f"SELECT * FROM users WHERE name = '{name}'"

# GOOD: Parameterized query
query = db.session.query(User).filter(User.name == name)
```

This is already done correctly in the application (using SQLAlchemy ORM).

### Status
✅ **HANDLED** - Proper parameterization in use

---

## Error: Connection Reset by Peer

### Symptoms
```
sqlalchemy.exc.OperationalError: 
(psycopg2.errors.OperationalError) Connection reset by peer
```

### Root Cause
Network interruption or database server restart.

### Solution (ALREADY IMPLEMENTED)
```python
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,  # ← Detects bad connections
    "max_overflow": 10,
    "pool_recycle": 1800,   # ← Recycles old connections
}
```

When a bad connection is detected, SQLAlchemy automatically creates a new one.

### Status
✅ **FIXED** - Automatic connection recovery enabled

---

## Monitoring & Debugging

### Enable SQL Logging
```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Check Database Connection
```python
# Test endpoint in app.py
@app.route("/health")
def health():
    try:
        with db.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "Database connection OK"
    except Exception as e:
        return f"Database connection failed: {str(e)}"
```

### Monitor Transaction Errors
```python
# Check logs for these patterns
[DB TRANSACTION ERROR]  # Transaction was aborted
[DB ROLLBACK ERROR]     # Rollback failed
[SESSION CLEANUP]       # Session cleanup warnings
```

---

## Quick Decision Tree

```
Database Error Occurred?
│
├─→ InFailedSqlTransaction?
│   └─→ Use db.session.rollback() + retry
│       ✅ IMPLEMENTED
│
├─→ Too many connections?
│   └─→ Use db.session.remove() in after_request
│       ✅ IMPLEMENTED
│
├─→ Connection reset/timeout?
│   └─→ Use pool_pre_ping and pool_recycle
│       ✅ IMPLEMENTED
│
├─→ Constraint violation (IntegrityError)?
│   └─→ Validate data before insert/update
│       ⚠️ CASE-BY-CASE
│
├─→ Deadlock?
│   └─→ Use safe_db_operation decorator for retries
│       ✅ AVAILABLE
│
├─→ Serialization failure?
│   └─→ Implement optimistic locking
│       ⚠️ CASE-BY-CASE
│
├─→ Query timeout?
│   └─→ Optimize query or implement pagination
│       ⚠️ REQUIRES OPTIMIZATION
│
└─→ Other error?
    └─→ Check logs and stack trace
        Use safe_db_operation pattern
        ✅ PATTERN AVAILABLE
```

---

## Testing Database Error Handling

### Simulate Transaction Error
```python
# In a route or test
from sqlalchemy import text
db.session.execute(text("INVALID SQL SYNTAX;"))
# Then try to query something
settings = SystemSettings.get_settings()  # Should recover
```

### Test Connection Pool
```python
# Open many connections and see recovery
for i in range(100):
    try:
        User.query.first()
    except Exception as e:
        print(f"Iteration {i}: {type(e).__name__}")
```

### Run Test Suite
```bash
python test_transaction_fix.py
```

---

## Summary Table

| Error | Status | Solution |
|-------|--------|----------|
| InFailedSqlTransaction | ✅ Fixed | Automatic rollback + retry |
| too many connections | ✅ Fixed | Session cleanup in after_request |
| Connection reset | ✅ Fixed | pool_pre_ping + pool_recycle |
| IntegrityError | ✅ Handled | Error handling pattern |
| Foreign Key Violation | ✅ Handled | Error handling pattern |
| Deadlock | ✅ Available | Use safe_db_operation decorator |
| Serialization Failure | ✅ Available | Use safe_db_operation decorator |
| Query Timeout | ⚠️ Manual | Optimize or paginate |
| Other Errors | ✅ Pattern | Use safe_db_operation pattern |

---

Last Updated: December 10, 2025
All fixes implemented and tested ✅
