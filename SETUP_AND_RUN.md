# How to Run the Project - Complete Setup Guide

## Prerequisites

1. **Docker Desktop** installed and running
2. **Python 3.9+** installed
3. **Node.js 16+** installed (for frontend)

---

## Step 1: Start the Database

```bash
cd /home/tw10576/major-v11

# Start PostgreSQL in Docker
docker compose up -d

# Verify database is running
docker ps
# You should see: shift_scheduler_db container running on port 5432
```

---

## Step 2: Setup Backend

```bash
cd /home/tw10576/major-v11/backend

# Install Python dependencies
pip install -r requirements.txt

# Initialize the database with admin user and test data
python init_db.py

# Seed mock data (employees, managers, departments, roles)
python seed_mock_data.py
```

**Output should show**:
```
✅ Database initialized!
✅ MOCK DATA SEEDING COMPLETE!
```

---

## Step 3: Start the Backend Server

```bash
cd /home/tw10576/major-v11/backend

# Start FastAPI server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

The API will be available at: **http://localhost:8000**  
Swagger UI: **http://localhost:8000/docs**

---

## Step 4: Start the Frontend (Optional - use for UI)

In a **NEW TERMINAL**:

```bash
cd /home/tw10576/major-v11/frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

**Expected Output**:
```
Local:   http://localhost:5173/
```

---

## Login Credentials

### Option 1: Login via API
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### Option 2: Login via Web UI
Go to **http://localhost:5173** and use:

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Manager | `manager1` | `manager123` |
| Employee | `emp1` | `emp123` |
| Employee | `emp2` | `emp123` |
| Employee | `emp3` | `emp123` |

---

## Troubleshooting Login Errors

### Error: "Incorrect username or password"

**Solution**: Ensure you initialized the database:
```bash
cd /home/tw10576/major-v11/backend
python init_db.py
python seed_mock_data.py
```

### Error: "Could not connect to database"

**Solution**: Check if PostgreSQL is running:
```bash
# Start Docker
docker compose up -d

# Verify connection
docker compose ps
```

### Error: "Module not found: openpyxl"

**Solution**: Install missing dependencies:
```bash
pip install -r requirements.txt
```

### Error: "Address already in use" on port 8000

**Solution**: Change the port:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Verify Everything is Working

### Test API Health
```bash
curl http://localhost:8000/docs
```

Should return the Swagger UI documentation page.

### Test Login
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | python -m json.tool
```

**Expected Response**:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
        "id": 1,
        "username": "admin",
        "email": "admin@company.com",
        "full_name": "Admin User",
        "user_type": "admin"
    }
}
```

### Test Employee Login  
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123" | python -m json.tool
```

---

## Run Tests

```bash
cd /home/tw10576/major-v11/backend

# Test leave workflow
bash /home/tw10576/major-v11/test_leave_flow.sh

# Test comprehensive features
bash /home/tw10576/major-v11/test_comprehensive.sh
```

---

## Quick Workflow Test

```bash
# 1. Create a leave request as emp1
TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "http://localhost:8000/leave-requests" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": 1,
    "start_date": "2025-12-28",
    "end_date": "2025-12-30",
    "leave_type": "paid_leave",
    "reason": "Testing"
  }' | python3 -m json.tool

# 2. Manager approves the leave
MGR_TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager1&password=manager123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST "http://localhost:8000/manager/approve-leave/1" \
  -H "Authorization: Bearer $MGR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"review_notes": "Approved"}' | python3 -m json.tool

# 3. Check notifications
curl -s -X GET "http://localhost:8000/notifications" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## Directory Structure

```
/home/tw10576/major-v11/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app (5295 lines)
│   │   ├── models.py         # Database models
│   │   ├── helpers.py        # NEW - Utility functions
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── database.py       # DB connection
│   │   ├── attendance_service.py
│   │   ├── wage_calculation_service.py
│   │   └── ...
│   ├── init_db.py            # Initialize database
│   ├── seed_mock_data.py     # Seed test data
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── docker-compose.yml        # PostgreSQL config
```

---

## What's Included

✅ **Bug Fixes** (5 critical issues fixed)
- Leave balance deduction working
- Notifications sent on approvals
- Attendance consistency checks
- Overtime approval workflows
- Leave type distinction

✅ **Core Features**
- Employee attendance tracking
- Leave management with balance
- Night work detection (22:00-06:00)
- Overtime tracking & approval
- Wage calculation & payroll cycles
- Notification system

✅ **Test Data**
- 1 Admin user
- 1 Manager + 3 Employees
- 2 Roles, 2 Shifts, 7 days of schedules
- Sample leave & overtime records

---

## Need Help?

1. **Check logs**: Look at the terminal where the backend is running
2. **Check database**: Verify Docker container is running
3. **Check port**: Make sure port 8000 is free
4. **Read errors**: The error message usually tells you what's wrong

For more details, see [BUG_FIXES_SUMMARY.md](BUG_FIXES_SUMMARY.md)
