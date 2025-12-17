#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"
TOKEN=""

# Function to print section header
print_header() {
    echo -e "\n${BLUE}===============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===============================================${NC}\n"
}

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local name=$4
    
    echo -e "${YELLOW}Testing: ${NC}$name"
    echo -e "${YELLOW}Method:${NC} $method $endpoint"
    
    if [ -z "$data" ]; then
        response=$(curl -s -X "$method" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            "$BASE_URL$endpoint")
    else
        echo -e "${YELLOW}Data:${NC} $data"
        response=$(curl -s -X "$method" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi
    
    # Check if response contains error
    if echo "$response" | grep -q "error\|detail"; then
        echo -e "${RED}❌ FAILED${NC}"
        echo "Response: $response"
    else
        echo -e "${GREEN}✓ SUCCESS${NC}"
        echo "Response: ${response:0:100}..."
    fi
    echo ""
}

# 1. GET TOKEN
print_header "1. AUTHENTICATION - Get Token"
response=$(curl -s -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=admin&password=admin123" \
    "$BASE_URL/token")

if echo "$response" | grep -q "access_token"; then
    echo -e "${GREEN}✓ SUCCESS${NC}"
    TOKEN=$(echo "$response" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    echo "Token: $TOKEN"
else
    echo -e "${RED}❌ FAILED${NC}"
    echo "Response: $response"
    exit 1
fi

# 2. GET CURRENT USER
print_header "2. AUTHENTICATION - Get Current User"
test_endpoint "GET" "/users/me" "" "Get Current User"

# 3. LIST USERS
print_header "3. USER MANAGEMENT - List Users"
test_endpoint "GET" "/admin/users" "" "List Users"

# 4. LIST DEPARTMENTS
print_header "4. DEPARTMENTS - List Departments"
test_endpoint "GET" "/departments" "" "List Departments"

# 5. SEARCH DEPARTMENT
print_header "5. DEPARTMENTS - Search Department"
test_endpoint "GET" "/departments/search/Assembly" "" "Search Department by Name"

# 6. LIST MANAGERS
print_header "6. MANAGERS - List Managers"
test_endpoint "GET" "/managers" "" "List Managers"

# 7. LIST EMPLOYEES
print_header "7. EMPLOYEES - List Employees"
test_endpoint "GET" "/employees" "" "List Employees"

# 8. LIST ROLES
print_header "8. ROLES - List Roles"
test_endpoint "GET" "/roles" "" "List Roles"

# 9. GET SCHEDULES
print_header "9. SCHEDULES - Get Schedules"
test_endpoint "GET" "/schedules" "" "Get Schedules"

# 10. GET LEAVE REQUESTS
print_header "10. LEAVE REQUESTS - List Leave Requests"
test_endpoint "GET" "/leave-requests" "" "List Leave Requests"

# 11. GET MESSAGES
print_header "11. MESSAGES - Get Messages"
test_endpoint "GET" "/messages" "" "Get Messages"

# 12. GET NOTIFICATIONS
print_header "12. NOTIFICATIONS - Get Notifications"
test_endpoint "GET" "/notifications" "" "Get Notifications"

# 13. GET ATTENDANCE
print_header "13. ATTENDANCE - Get Attendance"
test_endpoint "GET" "/attendance?start_date=2025-12-01&end_date=2025-12-31" "" "Get Attendance"

# 14. CREATE MANAGER (NEW)
print_header "14. MANAGERS - Create Manager (NEW USER)"
data='{"user_id": 4, "department_id": 1, "manager_emp_id": "10003", "manager_dept_id": "001"}'
test_endpoint "POST" "/managers" "$data" "Create New Manager"

# 15. CREATE MANAGER WITH CONFLICT
print_header "15. MANAGERS - Create Manager (With Conflict)"
data='{"user_id": 5, "department_id": 1, "manager_emp_id": "10004", "manager_dept_id": "001"}'
test_endpoint "POST" "/managers" "$data" "Create Manager (Conflict Expected)"

# 16. CREATE MANAGER WITH FORCE REASSIGN
print_header "16. MANAGERS - Create Manager (Force Reassign)"
test_endpoint "POST" "/managers?force_reassign=true" "$data" "Create Manager with Force Reassign"

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${GREEN}Testing Complete!${NC}"
echo -e "${BLUE}===============================================${NC}\n"
