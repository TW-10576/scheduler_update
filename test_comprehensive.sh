#!/bin/bash

# Comprehensive Test Suite for Leave Approval, Notifications, and Night Work

API_URL="http://localhost:8000"
PASS=0
FAIL=0

echo "=================================="
echo "COMPREHENSIVE SYSTEM TEST"
echo "=================================="

# Helper function to test and count results
test_case() {
  local name=$1
  local result=$2
  if [ "$result" -eq 0 ]; then
    echo "✅ PASS: $name"
    ((PASS++))
  else
    echo "❌ FAIL: $name"
    ((FAIL++))
  fi
}

# ==========TEST 1: LEAVE APPROVAL AND BALANCE DEDUCTION==========
echo -e "\n=== TEST 1: LEAVE APPROVAL & BALANCE DEDUCTION ==="

# Get emp1 token
EMP_TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

# Create leave request
LEAVE=$(curl -s -X POST "$API_URL/leave-requests" \
  -H "Authorization: Bearer $EMP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "start_date": "2025-12-24",
    "end_date": "2025-12-25",
    "leave_type": "paid_leave",
    "reason": "Test"
  }')

LEAVE_ID=$(echo "$LEAVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id', ''))" 2>/dev/null)
test_case "Leave request created" $([ ! -z "$LEAVE_ID" ] && echo 0 || echo 1)

# Get manager token
MGR_TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager1&password=manager123" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

# Approve leave
APPROVE=$(curl -s -X POST "$API_URL/manager/approve-leave/$LEAVE_ID" \
  -H "Authorization: Bearer $MGR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"review_notes": "Approved"}')

# Check if balance was deducted
DAYS_DEDUCTED=$(echo "$APPROVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('days_deducted', 0))" 2>/dev/null)
test_case "Leave balance deducted" $(python3 -c "print(0 if float('$DAYS_DEDUCTED') > 0 else 1)" 2>/dev/null || echo 1)

# ==========TEST 2: NOTIFICATIONS SENT==========
echo -e "\n=== TEST 2: NOTIFICATIONS SENT ==="

# Check notifications
NOTIF=$(curl -s -X GET "$API_URL/notifications" \
  -H "Authorization: Bearer $EMP_TOKEN")

NOTIF_COUNT=$(echo "$NOTIF" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len([x for x in d if x.get('notification_type') == 'leave_approved']))" 2>/dev/null)
test_case "Leave approval notification sent" $([ "$NOTIF_COUNT" -gt 0 ] && echo 0 || echo 1)

# ==========TEST 3: PAYROLL ENDPOINTS==========
echo -e "\n=== TEST 3: PAYROLL ENDPOINTS ==="

# Configure employee wage
WAGE_CONFIG=$(curl -s -X POST "$API_URL/payroll/configure-employee?employee_id=1&hourly_rate=500" \
  -H "Authorization: Bearer $MGR_TOKEN")

SUCCESS=$(echo "$WAGE_CONFIG" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null)
test_case "Employee wage configured" $([ "$SUCCESS" == "True" ] && echo 0 || echo 1)

# ==========SUMMARY==========
echo -e "\n=================================="
echo "TEST SUMMARY"
echo "=================================="
echo "PASSED: $PASS"
echo "FAILED: $FAIL"
echo "TOTAL:  $((PASS + FAIL))"
echo "=================================="

if [ $FAIL -eq 0 ]; then
  echo "✅ ALL TESTS PASSED!"
  exit 0
else
  echo "❌ SOME TESTS FAILED"
  exit 1
fi
