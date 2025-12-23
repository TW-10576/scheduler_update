#!/bin/bash

# Quick test of leave request creation
TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

echo "Token: ${TOKEN:0:20}..."

curl -s -X POST "http://localhost:8000/leave-requests" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 3,
    "start_date": "2025-12-28",
    "end_date": "2025-12-29",
    "leave_type": "paid_leave",
    "reason": "Test leave request"
  }' | python3 -m json.tool
