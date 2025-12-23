#!/bin/bash

# Check existing attendance data to verify night work calculations
echo "=== CHECKING EXISTING NIGHT WORK DATA ==="

# Get manager token
MGR_TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager1&password=manager123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo -e "\nFetching attendance records..."
curl -s -X GET "http://localhost:8000/attendance" \
  -H "Authorization: Bearer $MGR_TOKEN" | python3 << 'PYTHON'
import sys, json

data = json.load(sys.stdin)

print("\n" + "="*80)
print("ATTENDANCE RECORDS WITH NIGHT WORK")
print("="*80)

if isinstance(data, list):
    records = data
elif isinstance(data, dict) and 'data' in data:
    records = data['data']
else:
    records = []

for record in records:
    print(f"\nEmployee: {record.get('employee_id', '?')} | Date: {record.get('date', '?')}")
    print(f"  In Time: {record.get('in_time', '?')} | Out Time: {record.get('out_time', '?')}")
    print(f"  Worked Hours: {record.get('worked_hours', 0)}")
    print(f"  Night Hours: {record.get('night_hours', 0)}")
    print(f"  Night Allowance: {record.get('night_allowance', 0)}")
    print(f"  Overtime Hours: {record.get('overtime_hours', 0)}")

PYTHON
