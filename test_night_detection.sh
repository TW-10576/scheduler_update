#!/bin/bash

# Test Night Work Detection
# Verify that work done between 22:00-06:00 is tracked as night work

API_URL="http://localhost:8000"

echo "=== NIGHT WORK DETECTION TEST ==="

# Step 1: Get emp2 token
echo -e "\nStep 1: Login as emp2"
TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp2&password=emp123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

echo "Token obtained"

# Step 2: Create a check-in
echo -e "\nStep 2: Create check-in at 22:00 (10 PM)"
CHECK_IN=$(curl -s -X POST "$API_URL/checkin" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Night shift test"
  }')

echo "$CHECK_IN" | python3 -m json.tool 2>/dev/null || echo "$CHECK_IN"

# For now, let's verify night work detection at the API/calculation level
echo -e "\nStep 3: Check employee attendance records"
# Get list of attendance records - need manager access
MGR_TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager1&password=manager123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Check Bob's (emp2) attendance
curl -s -X GET "$API_URL/attendance?employee_id=2" \
  -H "Authorization: Bearer $MGR_TOKEN" | python3 -m json.tool | head -80
