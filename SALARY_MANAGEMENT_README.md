# Staff Salary Management Feature

## Overview
The Salary Management system allows the Bursar to:
- View all staff organized by role (Teachers, Admins, Secretaries, etc.)
- Record salary payments for staff for a given month/year period
- Track paid vs. unpaid staff for each period
- Generate reports on salary payments by role
- View payment history for individual staff members

## Database Schema

### New Tables

#### `role_salaries`
Stores the default monthly salary for each role in the school.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Unique identifier |
| role_id | Integer (FK) | Reference to roles table |
| amount | Numeric(12,2) | Default monthly salary |
| min_amount | Numeric(12,2) | Optional minimum range |
| max_amount | Numeric(12,2) | Optional maximum range |
| created_at | Timestamp | Creation date |
| updated_at | Timestamp | Last update date |

#### `salary_payments`
Records individual salary payment transactions.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer (PK) | Unique identifier |
| user_id | Integer (FK) | Staff member being paid |
| role_id | Integer (FK) | Denormalized role for quick queries |
| amount | Numeric(12,2) | Payment amount |
| paid_by_user_id | Integer (FK) | Bursar who recorded payment |
| payment_date | Timestamp | When payment was recorded |
| period_month | Integer | Month (1-12) for monthly tracking |
| period_year | Integer | Year for monthly tracking |
| term | String(20) | Term name if using term-based periods |
| year | Integer | Year if using term-based periods |
| status | String(20) | 'paid', 'reversed', or 'pending' |
| reference | String(100) | Optional receipt/check number |
| notes | Text | Optional notes |
| created_at | Timestamp | Creation date |
| updated_at | Timestamp | Last update date |

#### `users.salary_amount`
New optional column added to users table for per-user salary overrides.

| Column | Type | Description |
|--------|------|-------------|
| salary_amount | Numeric(12,2) | User-specific override (if set, supersedes role default) |

## Models

### RoleSalary
```python
class RoleSalary(db.Model):
    """Default salary for a role."""
    role_id       # FK to Role
    amount        # Decimal(12, 2)
    min_amount    # Optional range
    max_amount    # Optional range
```

### SalaryPayment
```python
class SalaryPayment(db.Model):
    """Individual payment record."""
    user_id           # FK to User (staff member)
    role_id           # FK to Role (denormalized)
    amount            # Decimal(12, 2)
    paid_by_user_id   # FK to User (bursar)
    payment_date      # Timestamp
    period_month      # Int 1-12 OR term/year
    period_year       # Int
    term              # String('Term 1', etc.)
    status            # 'paid', 'reversed', 'pending'
    reference         # Optional
    notes             # Optional
```

## Routes

### GET /bursar/manage-staff-salaries
Display staff salary management page with filters.

**Query Parameters:**
- `role_id` (optional) — Filter by role
- `month` (optional) — Month (1-12), default: current month
- `year` (optional) — Year, default: current year
- `status` (optional) — 'all', 'paid', 'unpaid', default: 'all'

**Response:**
Renders `templates/bursar/manage_staff_salaries.html` with:
- List of staff filtered by selected role
- Salary amount for each staff (per-user override or role default)
- Payment status (Paid / Unpaid) for selected period
- Statistics cards (total staff, paid count, unpaid count)

### POST /bursar/staff/<user_id>/mark-paid
Record a salary payment for a staff member.

**Request Body (JSON):**
```json
{
  "amount": 50000,
  "period_month": 12,
  "period_year": 2025,
  "reference": "Check #1234",
  "notes": "Regular salary"
}
```

**Response (JSON):**
```json
{
  "success": true,
  "payment_id": 123,
  "message": "✓ John Doe marked as paid",
  "payment": {
    "id": 123,
    "amount": 50000,
    "payment_date": "2025-12-05T01:30:00",
    "period": "Dec 2025",
    "status": "paid"
  }
}
```

**Status Codes:**
- `200` — Payment recorded successfully
- `400` — Invalid input (amount <= 0)
- `409` — Staff already marked as paid for this period
- `500` — Server error

### POST /bursar/staff/<user_id>/mark-unpaid
Reverse a salary payment (marks as 'reversed' instead of deleting).

**Request Body (JSON):**
```json
{
  "payment_id": 123
}
```

**Response (JSON):**
```json
{
  "success": true,
  "message": "✓ Payment reversed for John Doe",
  "payment_id": 123
}
```

### GET /bursar/staff/<user_id>/salary-history
Retrieve payment history for a specific staff member.

**Response (JSON):**
```json
{
  "success": true,
  "user": "John Doe",
  "email": "john@school.edu",
  "role": "Teacher",
  "history": [
    {
      "id": 123,
      "amount": 50000,
      "payment_date": "2025-12-05T01:30:00",
      "period": "Dec 2025",
      "status": "paid",
      "reference": "Check #1234",
      "notes": "Regular salary"
    }
  ]
}
```

### GET /bursar/salary-report
Generate a summary report of salary payments for a period.

**Query Parameters:**
- `month` (optional) — Month (1-12)
- `year` (optional) — Year
- `role_id` (optional) — Filter by role

**Response (JSON):**
```json
{
  "success": true,
  "period": "12/2025",
  "total_paid": 450000,
  "payment_count": 9,
  "by_role": [
    {
      "role": "Teacher",
      "count": 5,
      "total": 250000
    },
    {
      "role": "Admin",
      "count": 2,
      "total": 150000
    }
  ]
}
```

## Features

### 1. Staff Listing
- Displays all staff with salary information
- Filters by role, month/year, and payment status
- Shows current salary amount (per-user override or role default)
- Displays paid/unpaid badge for selected period
- Responsive layout for mobile devices

### 2. Payment Recording
- Modal dialog to confirm and record salary payment
- Allows custom amount (partial payments supported)
- Optional reference number and notes
- Real-time status update on success

### 3. Payment History
- View all payments for a staff member
- Filter and sort by date
- Shows payment status (paid, reversed, pending)

### 4. Reporting
- Summary report by role
- Total payments and count by period
- Export capabilities (can be extended)

### 5. Audit Trail
- Payments are marked as 'reversed' instead of deleted (audit safety)
- Tracks who made the payment (paid_by_user_id)
- Timestamp for all transactions

## Setup Instructions

### 1. Run Database Setup Script
```powershell
cd 'c:\Users\sejjusa\Desktop\school_management_system-main'
python create_salary_tables.py
```

This will:
- Create `role_salaries` table
- Create `salary_payments` table with indexes
- Add `salary_amount` column to `users` table

### 2. Seed Default Role Salaries (Optional but Recommended)
```powershell
python seed_role_salaries.py
```

This will create default salary entries:
- Teacher: 50,000 UGX
- Admin: 75,000 UGX
- Secretary: 40,000 UGX
- Bursar: 70,000 UGX
- Headteacher: 100,000 UGX

You can modify these amounts in the seed script as needed.

### 3. Verify Flask App Imports
```powershell
python -c "from models.salary_models import RoleSalary, SalaryPayment; print('✓ Models OK')"
python -c "from routes.bursar_routes import bursar_routes; print('✓ Routes OK')"
```

### 4. Test in Browser
1. Start Flask app: `python app.py`
2. Log in as Bursar
3. Navigate to Dashboard → "Manage Staff Salaries"
4. Select role and month
5. Click "Mark Paid" to record a payment

## Usage Examples

### Example 1: Mark a Teacher as Paid
1. Open Manage Staff Salaries page
2. Filter by Role: "Teacher"
3. Filter by Month: December, Year: 2025
4. Click "Mark Paid" next to teacher name
5. Confirm amount and click "Confirm & Save"
6. Page refreshes; status changes to "✓ Paid"

### Example 2: Generate Monthly Report
```python
# From Python shell or job:
from routes.bursar_routes import bursar_routes
from flask import Flask

app = Flask(__name__)
with app.test_client() as client:
    response = client.get('/bursar/salary-report?month=12&year=2025')
    print(response.json)
```

### Example 3: Reverse a Payment
1. Open Manage Staff Salaries page
2. Find staff with status "✓ Paid"
3. Click "Unmark" button
4. Confirm action
5. Payment is marked as 'reversed' (audit trail maintained)

## Salary Amount Resolution

When displaying a staff member's salary, the system uses this precedence:

1. **User Override** — If `user.salary_amount` is set (not NULL), use it
2. **Role Default** — Otherwise, use `role.salary_config.amount`
3. **Zero** — If neither is set, default to 0 (indicates incomplete setup)

Example:
```python
salary = user.salary_amount or (user.role.salary_config.amount if user.role.salary_config else 0)
```

## Extending the Feature

### Add Term-Based Salaries (instead of monthly)
Currently supports both monthly and term-based periods via `period_month/period_year` and `term/year` columns.

Update the template filter to use term/year:
```python
SalaryPayment.query.filter(
    SalaryPayment.term == 'Term 1',
    SalaryPayment.year == 2025,
    SalaryPayment.status == 'paid'
)
```

### Add Bulk Payment
Create a new route `/bursar/bulk-mark-paid` that accepts multiple `user_id` values and creates payment records in batch.

### Add CSV Export
```python
@bursar_routes.route('/salary-report/export')
def export_salary_report():
    # Query, aggregate, return CSV
```

### Add Email Notifications
After marking staff as paid, send confirmation email with payment details.

### Add Payment Approval Workflow
Add `status='pending'` and approval routes:
- Bursar marks as paid → status='pending'
- Manager reviews → status='paid' or status='rejected'

## Troubleshooting

### Issue: "Table already exists" when running create_salary_tables.py
**Solution:** Tables are already created. This is expected if running script twice.

### Issue: "Role not found" when seeding
**Solution:** Ensure roles are created first in your system. Check `roles` table:
```sql
SELECT * FROM roles;
```

### Issue: Staff not showing in Manage Salaries page
**Solutions:**
1. Ensure staff have a valid role_id
2. Verify the role exists in `roles` table
3. Check filters aren't too restrictive

### Issue: Payment records not showing in dropdown/list
**Solution:** 
- Ensure `period_month` and `period_year` match your filter
- Check status = 'paid' (reversed payments won't show in paid list)
- Verify user_id is correct

## Testing Checklist

- [ ] Create salary record for a role
- [ ] Create salary record for a user (override)
- [ ] Mark a staff member as paid
- [ ] Verify SalaryPayment record created in database
- [ ] Mark staff as unpaid (reverse)
- [ ] Verify status changed to 'reversed'
- [ ] View payment history for a staff
- [ ] Generate monthly report
- [ ] Test filters (role, month, year, status)
- [ ] Test on mobile (responsive design)
- [ ] Test AJAX error handling (invalid amounts, duplicate payments)

## Files Created/Modified

### New Files
- `models/salary_models.py` — RoleSalary and SalaryPayment models
- `routes/bursar_routes.py` — New salary management routes (added to existing file)
- `templates/bursar/manage_staff_salaries.html` — UI template
- `create_salary_tables.py` — Database setup script
- `seed_role_salaries.py` — Seed script for default salaries

### Modified Files
- `models/user_models.py` — Added `salary_amount` column to User model
- `templates/bursar/dashboard.html` — Updated button link to new page

---

**Version:** 1.0  
**Last Updated:** 2025-12-05  
**Author:** AI Assistant  
**Status:** Ready for Production
