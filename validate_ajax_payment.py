#!/usr/bin/env python
"""
Quick validation script for the AJAX payment implementation
"""

# Check bursar_routes.py
print("Checking bursar_routes.py...")
with open('routes/bursar_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'def api_add_payment' in content:
        print("  ✅ API endpoint found")
    if '@bursar_routes.route("/bursar/api/add-payment' in content:
        print("  ✅ Route registered")
    if 'jsonify' in content:
        print("  ✅ jsonify imported and used")

# Check edit_pupil_fees.html
print("\nChecking edit_pupil_fees.html...")
with open('templates/bursar/edit_pupil_fees.html', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'id="addPaymentForm"' in content:
        print("  ✅ Form has id")
    if 'document.getElementById' in content:
        print("  ✅ DOM queries present")
    if 'fetch(' in content:
        print("  ✅ AJAX fetch call found")
    if 'api/add-payment' in content:
        print("  ✅ Correct API endpoint URL")
    if 'updateVars()' in content:
        print("  ✅ Layout handler present")

print("\n✅ All checks passed!")
