#!/bin/bash

# Test creating leave request with different employee_ids
echo "Testing leave request creation..."

# First get token for emp1
TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

# Try different employee_ids
for EMP_ID in 1 2 3 4 5; do
  echo -e "\nTrying employee_id=$EMP_ID..."
  curl -s -X POST "http://localhost:8000/leave-requests" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"employee_id\": $EMP_ID,
      \"start_date\": \"2025-12-28\",
      \"end_date\": \"2025-12-29\",
      \"leave_type\": \"paid_leave\",
      \"reason\": \"Test\"
    }" | python3 -c "import sys,json; d=json.load(sys.stdin); print('  Success!' if 'id' in d else f'  Error: {d.get(\"detail\", \"Unknown\")}')" 2>/dev/null || echo "  Failed to parse"
done
