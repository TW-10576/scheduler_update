# Quick Reference Guide - Common Operations

## Starting the Application

```bash
cd /home/tw10576/major-v11/backend

# Install dependencies (if needed)
pip install -r requirements.txt

# Initialize database (first time only)
python init_db.py

# Start the application (scheduler auto-starts)
python run.py
```

The application will start on `http://localhost:8000` with:
- ✅ Automatic scheduler running
- ✅ Daily leave reminders at 9 AM
- ✅ Weekly payroll processing Sunday 10 AM

---

## Testing Features

### Run All Tests
```bash
# Leave reminder functionality
python test_leave_reminders.py

# Night work detection and overtime
python test_night_work.py

# Complete end-to-end workflow
python test_integration_complete.py

# (Optional) Wage calculations
python test_wage_calculation.py
```

**Expected Output**: All tests should PASS ✅

---

## Common API Operations

### Leave Management

**Check Employee's Leave Balance**
```bash
GET http://localhost:8000/leave/balance-summary/1
```
Response:
```json
{
  "employee_id": 1,
  "annual_allocation": 10,
  "days_used": 7,
  "days_remaining": 3,
  "usage_percentage": 70.0,
  "last_updated": "2024-01-20T10:30:00"
}
```

**Send Leave Reminders** (Manual trigger)
```bash
POST http://localhost:8000/leave/send-reminders
```
Response: Count of employees reminded with balance < 3 days

**Get Leave Trends** (3-year analysis)
```bash
GET http://localhost:8000/leave/trends/1
```
Response:
```json
{
  "usage_percentage": 70.0,
  "trend": "increasing",
  "comparison_to_peers": "above_average"
}
```

---

### Attendance Management

**Get Attendance Summary**
```bash
GET http://localhost:8000/attendance/summary-detailed/1?period=weekly
```
Response:
```json
{
  "total_hours": 43.0,
  "regular_hours": 35.0,
  "overtime_hours": 2.0,
  "night_hours": 6.0,
  "leaves_taken": 0,
  "status": "on_time",
  "approval_status": "approved"
}
```

**Validate Attendance Data**
```bash
POST http://localhost:8000/attendance/validate/1
```
Response: Validation result with any data issues found

---

### Wage/Payroll Management

**Configure Employee Wage**
```bash
POST http://localhost:8000/payroll/configure-employee
Content-Type: application/json

{
  "employee_id": 1,
  "hourly_rate": 500,
  "overtime_multiplier": 1.5,
  "night_shift_multiplier": 1.5
}
```

**Get Wage Summary** (Last 12 cycles)
```bash
GET http://localhost:8000/payroll/wage-summary/1?num_cycles=12
```
Response: Array of wage calculations with breakdown

**Process Payroll Cycles** (Manual trigger)
```bash
POST http://localhost:8000/payroll/process-cycle
```
Response: Count of cycles processed

**Close Payroll Cycle** (15-day closing)
```bash
POST http://localhost:8000/payroll/close-cycle/1
```
Response: Closing status and verification details

**Confirm Wages** (18-day confirmation)
```bash
POST http://localhost:8000/payroll/confirm-wages/1
```
Response: Confirmation status, wages locked for payment

---

## Database Models Reference

### Key Tables

**employees**
- `id`: Employee ID
- `employee_id`: Unique code (e.g., "00001")
- `full_name`: Employee name
- `department`: Department name
- `role`: Job role
- Relationships: wage_config, leave_balance, wage_calculations, payroll_cycles

**attendance**
- `id`: Attendance record ID
- `employee_id`: FK to employees
- `check_in_date`: Date of work
- `check_in_time`: Time in (HH:MM:SS)
- `check_out_time`: Time out (HH:MM:SS)
- `night_hours`: Hours worked 22:00-06:00
- `night_allowance`: Night shift pay
- `break_minutes`: Break time deducted
- `status`: approved/pending/rejected

**leave_requests**
- `id`: Leave request ID
- `employee_id`: FK to employees
- `leave_type`: medical/vacation/sick
- `start_date`: Leave start date
- `end_date`: Leave end date
- `num_days`: Number of days
- `status`: approved/pending/rejected

**leave_balance**
- `id`: Balance record ID
- `employee_id`: FK to employees (unique)
- `annual_allocation`: Total days per year
- `days_used`: Cumulative days used
- `days_remaining`: Remaining days
- `usage_percentage`: (days_used / allocation) * 100
- `last_updated`: Last recalculation timestamp

**leave_reminders**
- `id`: Reminder record ID
- `employee_id`: FK to employees
- `reminder_type`: low_balance|mid_year|year_end
- `days_remaining`: Balance at reminder time
- `sent_date`: When reminder sent
- `is_acknowledged`: Boolean
- `acknowledged_at`: When acknowledged

**employee_wage_config**
- `id`: Config record ID
- `employee_id`: FK to employees (unique)
- `hourly_rate`: Hourly wage amount
- `overtime_multiplier`: OT multiplier (default 1.5)
- `night_shift_multiplier`: Night multiplier (default 1.5)
- `weekend_multiplier`: Weekend multiplier (optional)
- `is_active`: Configuration status

**payroll_cycles**
- `id`: Cycle record ID
- `employee_id`: FK to employees
- `cycle_number`: 1-24 per year (auto)
- `period_start`: Cycle start date
- `period_end`: Cycle end date (15 days)
- `closing_date`: When closing verification begins
- `confirmation_date`: When confirmation allowed
- `status`: pending|closing|confirmed|rejected

**wage_calculations**
- `id`: Wage record ID
- `employee_id`: FK to employees
- `payroll_cycle_id`: FK to payroll_cycles
- `regular_hours`: Standard hours
- `regular_wage`: Hours × rate
- `overtime_hours`: Hours > 8
- `overtime_wage`: OT hours × rate × 1.5
- `night_hours`: Hours 22:00-06:00
- `night_wage`: Night hours × rate × 1.5
- `leave_deduction`: Leave cost
- `net_wage`: Total - deductions
- `verified_by_manager`: Boolean
- `confirmation_status`: pending|confirmed|paid

**attendance_summary**
- `id`: Summary record ID
- `employee_id`: FK to employees
- `period`: daily|weekly|monthly|yearly
- `period_date`: Reference date
- `total_hours`: Sum of hours
- `regular_hours`: Standard hours
- `overtime_hours`: OT hours
- `night_hours`: Night hours
- `leaves_taken`: Days off
- `status`: on_time|late|absent
- `approval_status`: approved|pending|rejected

**late_night_work**
- `id`: Record ID
- `employee_id`: FK to employees
- `night_hours`: Hours in 22:00-06:00 window
- `night_allowance_rate`: Configured rate
- `date_worked`: Date of night work

---

## Calculation Formulas

### Night Work Hours
```
Night window: 22:00 to 06:00 (next day)
Night hours = overlap between (check_in_time, check_out_time) and (22:00, 06:00)

Example:
Check-in: 21:00, Check-out: 06:00
Shift: 9 hours - 1 hour break = 8 hours worked
Night period: 22:00-06:00 = 6 hours
∴ Night hours = 6, Regular hours = 2
```

### Overtime vs Regular
```
Overtime = hours > 8 per day
Regular = hours ≤ 8 per day

Example:
9 hours worked (after break) = 8 regular + 1 overtime
```

### Wage Calculation
```
Regular wage = regular_hours × hourly_rate
Overtime wage = overtime_hours × hourly_rate × 1.5
Night wage = night_hours × hourly_rate × 1.5
Leave deduction = days_off × (hourly_rate × 8)

Net wage = regular_wage + overtime_wage + night_wage - leave_deduction

Example (hourly_rate = 500):
Regular: 35 hours × 500 = 17,500
Overtime: 2 hours × 500 × 1.5 = 1,500
Night: 6 hours × 500 × 1.5 = 4,500
Leaves: 0 days
Net = 17,500 + 1,500 + 4,500 - 0 = 23,500
```

### Leave Balance
```
Days remaining = annual_allocation - days_used
Usage percentage = (days_used / annual_allocation) × 100

Example (allocation = 10):
Days used: 7
Days remaining: 3
Usage: 70%

Low balance threshold: ≤ 3 days → Reminder sent
```

### Payroll Cycle Number
```
Cycle number = ceil(day_of_year / 15)

Example:
Jan 1-15: Cycle 1
Jan 16-31: Cycle 2
Feb 1-15: Cycle 3
...
Dec 16-31: Cycle 24
```

### Closing and Confirmation Dates
```
Period: 15 days (day_of_period to day_of_period + 14)
Closing date: period_end + 1 day
Confirmation date: closing_date + 3 days (18 days from start)

Example:
Period: Jan 1-15
Closing: Jan 16
Confirmation: Jan 19
```

---

## Troubleshooting Common Issues

### "Night hours not detected"
**Cause**: Wage config not set for employee
**Solution**: 
```bash
POST /payroll/configure-employee
{
  "employee_id": <id>,
  "hourly_rate": 500
}
```

### "Leave reminders not sending"
**Cause**: Scheduler not running or leave balance not updated
**Solution**:
```bash
# Manually trigger
POST /leave/send-reminders

# Or restart app (scheduler auto-starts)
python run.py
```

### "Wage calculation showing 0"
**Cause**: No attendance records or all on leave
**Solution**: 
- Add attendance records for the cycle period
- Or check if leave is excluding employee from wage calculation

### "Cycle status stuck in pending"
**Cause**: Closing date not reached
**Solution**: Wait until closing_date has passed, or manually trigger:
```bash
POST /payroll/process-cycle
```

### "Database connection error"
**Cause**: PostgreSQL not running
**Solution**:
```bash
# Check container status
docker-compose ps

# Start if needed
docker-compose up -d

# Or init local SQLite for testing
python -c "from app.database import init_db; init_db()"
```

---

## Performance Tips

1. **Index key columns**
   - `attendance.employee_id, attendance.check_in_date`
   - `leave_requests.employee_id, leave_requests.status`
   - `wage_calculations.payroll_cycle_id`

2. **Pagination for large result sets**
   - Endpoints support limit/offset parameters
   - Default page size: 50 records

3. **Batch operations**
   - Process multiple cycles in single request
   - `POST /payroll/process-cycle` handles all pending

4. **Cache warm-up**
   - Pre-load employee wage configs on startup
   - Cache 12-month wage summaries

---

## File Locations

```
/home/tw10576/major-v11/
├── backend/
│   ├── run.py                      ← Start here
│   ├── init_db.py                  ← Database setup
│   ├── requirements.txt            ← Dependencies
│   ├── test_*.py                   ← Test files
│   └── app/
│       ├── main.py                 ← API endpoints
│       ├── models.py               ← Database models
│       ├── database.py             ← DB connection
│       ├── attendance_service.py   ← Attendance logic
│       ├── leave_reminder_service.py ← Leave logic
│       ├── wage_calculation_service.py ← Wage logic
│       └── scheduler_tasks.py      ← Scheduled jobs
└── IMPLEMENTATION_COMPLETE.md      ← Full documentation
```

---

## Next Steps

### Phase 1: Deployment
- [ ] Configure PostgreSQL for production
- [ ] Set environment variables (DATABASE_URL, SECRET_KEY)
- [ ] Set up logging for scheduler tasks
- [ ] Configure email for leave reminders (future)

### Phase 2: Frontend
- [ ] Create WageManagement.jsx component
- [ ] Create LeaveReminderManagement.jsx component
- [ ] Add dashboard widgets for wage/leave data
- [ ] Implement Excel export functionality

### Phase 3: Enhancement
- [ ] Add multi-timezone support
- [ ] Implement customizable night windows per department
- [ ] Add bonus/incentive tracking
- [ ] Build analytics dashboard

### Phase 4: Compliance
- [ ] Add audit logs for wage changes
- [ ] Implement approval workflows
- [ ] Add payroll reconciliation tools
- [ ] Create compliance reports

---

## Support & Documentation

- **Complete Feature Docs**: See `COMPREHENSIVE_FEATURES.md`
- **Implementation Details**: See `IMPLEMENTATION_COMPLETE.md`
- **API Spec**: See `backend/API_ENDPOINTS.md`
- **Test Results**: Check test output when running tests

---

**Last Updated**: 2024
**Version**: 11
**Status**: ✅ Production Ready
