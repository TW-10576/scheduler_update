#!/bin/bash

# Simple test to understand the leave request flow

echo "=== LEAVE REQUEST TEST ===" 

# Step 1: Get employee token
echo -e "\nStep 1: Login as emp1"
EMP_TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

echo "Token obtained"

# Step 2: Try to create leave request - first find out what employee_id to use
# The error message says "Can only request leave for yourself", which means we need to use the right employee_id
# Let's try employee_id=1
echo -e "\nStep 2: Create leave request with employee_id=1"
LEAVE_RESP=$(curl -s -X POST "http://localhost:8000/leave-requests" \
  -H "Authorization: Bearer $EMP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "start_date": "2025-12-28",
    "end_date": "2025-12-30",
    "leave_type": "paid_leave",
    "reason": "Test leave request"
  }')

echo "$LEAVE_RESP" | python3 -m json.tool

# Extract leave_id if successful
LEAVE_ID=$(echo "$LEAVE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id', 'NOTFOUND'))" 2>/dev/null)
echo -e "\nLeave ID: $LEAVE_ID"

if [ "$LEAVE_ID" != "NOTFOUND" ] && [ ! -z "$LEAVE_ID" ]; then
  # Step 3: Get manager token
  echo -e "\nStep 3: Login as manager"
  MGR_TOKEN=$(curl -s http://localhost:8000/token -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=manager1&password=manager123" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

  echo "Manager token obtained"

  # Step 4: Approve leave
  echo -e "\nStep 4: Manager approves leave"
  APPROVE_RESP=$(curl -s -X POST "http://localhost:8000/manager/approve-leave/$LEAVE_ID" \
    -H "Authorization: Bearer $MGR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "review_notes": "Approved"
    }')

  echo "$APPROVE_RESP" | python3 -m json.tool

  # Step 5: Check leave balance
  echo -e "\nStep 5: Check leave balance"
  BALANCE=$(curl -s -X GET "http://localhost:8000/leave/balance-summary/1" \
    -H "Authorization: Bearer $EMP_TOKEN")

  echo "$BALANCE" | python3 -m json.tool
fi
