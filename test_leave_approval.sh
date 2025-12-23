#!/bin/bash

# Test Leave Approval Workflow
# This script tests: 1) Create leave request 2) Approve it 3) Verify balance deduction and notification

API_URL="http://localhost:8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}====== LEAVE APPROVAL WORKFLOW TEST ======${NC}"

# Step 1: Login as employee
echo -e "\n${YELLOW}Step 1: Login as employee${NC}"
EMPLOYEE_LOGIN=$(curl -s -X POST "$API_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123")

EMPLOYEE_TOKEN=$(echo $EMPLOYEE_LOGIN | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo -e "${GREEN}Employee token: ${EMPLOYEE_TOKEN:0:20}...${NC}"

EMPLOYEE_REQUEST=$(curl -s -X GET "$API_URL/users/me" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN")

EMPLOYEE_ID=$(echo $EMPLOYEE_REQUEST | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
USER_ID=$(echo $EMPLOYEE_REQUEST | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('id', ''))")
echo -e "${GREEN}Employee ID: $EMPLOYEE_ID${NC}"

# Step 2: Create a leave request
echo -e "\n${YELLOW}Step 2: Create leave request for next week (paid_leave)${NC}"
START_DATE=$(date -d "+5 days" +%Y-%m-%d)
END_DATE=$(date -d "+6 days" +%Y-%m-%d)

LEAVE_REQUEST=$(curl -s -X POST "$API_URL/leave-requests" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"start_date\": \"$START_DATE\",
    \"end_date\": \"$END_DATE\",
    \"leave_type\": \"paid_leave\",
    \"reason\": \"Personal reason - testing\"
  }")

LEAVE_ID=$(echo $LEAVE_REQUEST | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
echo -e "${GREEN}Leave request created with ID: $LEAVE_ID${NC}"
echo "Request: $LEAVE_REQUEST"

# Step 3: Get initial leave balance
echo -e "\n${YELLOW}Step 3: Get initial leave balance${NC}"
INITIAL_BALANCE=$(curl -s -X GET "$API_URL/leave/balance-summary/$EMPLOYEE_ID" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN")

INITIAL_REMAINING=$(echo $INITIAL_BALANCE | grep -o '"remaining_paid_leave":[0-9.]*' | cut -d':' -f2)
echo -e "${GREEN}Initial remaining leave: $INITIAL_REMAINING days${NC}"

# Step 4: Login as manager
echo -e "\n${YELLOW}Step 4: Login as manager${NC}"
MANAGER_LOGIN=$(curl -s -X POST "$API_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager1&password=manager123")

MANAGER_TOKEN=$(echo $MANAGER_LOGIN | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo -e "${GREEN}Manager token: ${MANAGER_TOKEN:0:20}...${NC}"

# Step 5: Approve leave
echo -e "\n${YELLOW}Step 5: Manager approves leave${NC}"
APPROVAL=$(curl -s -X POST "$API_URL/manager/approve-leave/$LEAVE_ID" \
  -H "Authorization: Bearer $MANAGER_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"review_notes\": \"Approved\"
  }")

echo -e "${GREEN}Approval response:${NC}"
echo $APPROVAL | python3 -m json.tool 2>/dev/null || echo $APPROVAL

# Step 6: Get updated balance
echo -e "\n${YELLOW}Step 6: Get updated leave balance${NC}"
UPDATED_BALANCE=$(curl -s -X GET "$API_URL/leave/balance-summary/$EMPLOYEE_ID" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN")

UPDATED_REMAINING=$(echo $UPDATED_BALANCE | grep -o '"remaining_paid_leave":[0-9.]*' | cut -d':' -f2)
echo -e "${GREEN}Updated remaining leave: $UPDATED_REMAINING days${NC}"

# Step 7: Verify balance was deducted
echo -e "\n${YELLOW}Step 7: Verify balance deduction${NC}"
DAYS_DIFF=$(echo "$INITIAL_REMAINING - $UPDATED_REMAINING" | bc)
echo -e "${GREEN}Days deducted: $DAYS_DIFF${NC}"

if [ $(echo "$DAYS_DIFF > 0" | bc) -eq 1 ]; then
  echo -e "${GREEN}✓ Balance was correctly deducted${NC}"
else
  echo -e "${RED}✗ Balance was NOT deducted (issue!)${NC}"
fi

# Step 8: Check notifications
echo -e "\n${YELLOW}Step 8: Check employee notifications${NC}"
NOTIFICATIONS=$(curl -s -X GET "$API_URL/notifications" \
  -H "Authorization: Bearer $EMPLOYEE_TOKEN")

echo -e "${GREEN}Notifications:${NC}"
echo $NOTIFICATIONS | python3 -m json.tool 2>/dev/null || echo $NOTIFICATIONS

# Count leave_approved notifications
LEAVE_APPROVED_COUNT=$(echo $NOTIFICATIONS | grep -o '"notification_type":"leave_approved"' | wc -l)
echo -e "${GREEN}Leave approved notifications: $LEAVE_APPROVED_COUNT${NC}"

if [ $LEAVE_APPROVED_COUNT -gt 0 ]; then
  echo -e "${GREEN}✓ Notification was created${NC}"
else
  echo -e "${RED}✗ Notification was NOT created (issue!)${NC}"
fi

echo -e "\n${YELLOW}====== TEST COMPLETE ======${NC}"
