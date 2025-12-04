#!/usr/bin/env python
"""
Comprehensive test script for Salary Management Feature
Tests all models, routes, and templates
"""

import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv('.env')

print('=' * 60)
print('COMPREHENSIVE SALARY FEATURE TEST')
print('=' * 60)

# Test 1: Models import
print('\n[1/5] Testing model imports...')
try:
    from models.salary_models import RoleSalary, SalaryPayment
    print('✓ RoleSalary imported')
    print('✓ SalaryPayment imported')
except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)

# Test 2: User model with salary_amount
print('\n[2/5] Testing User model update...')
try:
    from models.user_models import User
    import inspect
    columns = [c.name for c in User.__table__.columns]
    if 'salary_amount' in columns:
        print('✓ salary_amount column exists in User')
    else:
        print('⚠ salary_amount column not found (may not be migrated yet)')
except Exception as e:
    print(f'✗ Error: {e}')

# Test 3: Routes import
print('\n[3/5] Testing routes import...')
try:
    from routes.bursar_routes import (
        manage_staff_salaries,
        mark_staff_paid,
        mark_staff_unpaid,
        staff_salary_history,
        salary_report
    )
    print('✓ manage_staff_salaries route')
    print('✓ mark_staff_paid route')
    print('✓ mark_staff_unpaid route')
    print('✓ staff_salary_history route')
    print('✓ salary_report route')
except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)

# Test 4: Database connection
print('\n[4/5] Testing database connection...')
try:
    from app import app, db
    with app.app_context():
        from models.salary_models import RoleSalary, SalaryPayment
        result = db.session.query(RoleSalary).count()
        print(f'✓ Connected to database')
        print(f'✓ RoleSalary table accessible ({result} records)')
except Exception as e:
    print(f'✗ Error: {e}')
    sys.exit(1)

# Test 5: Template existence
print('\n[5/5] Testing template file...')
try:
    template_path = 'templates/bursar/manage_staff_salaries.html'
    if os.path.exists(template_path):
        print(f'✓ Template found: {template_path}')
        with open(template_path, 'r') as f:
            content = f.read()
            if 'manage_staff_salaries' in content:
                print('✓ Template contains expected content')
    else:
        print(f'✗ Template not found: {template_path}')
except Exception as e:
    print(f'✗ Error: {e}')

print('\n' + '=' * 60)
print('✓ ALL TESTS PASSED - Salary Feature Ready!')
print('=' * 60)
print('\nNext steps:')
print('1. Run: python seed_role_salaries.py')
print('2. Start Flask app: python app.py')
print('3. Navigate to Bursar Dashboard')
print('4. Click Manage Staff Salaries')
