# Comprehensive Attendance & Wage Management System

## Overview

This document describes the complete implementation of comprehensive employee attendance management, paid leave reminders, late-night work hour detection, and part-time wage calculation features.

## Features Implemented

### 1. Comprehensive Attendance Data Management

**Models:**
- `Attendance` - Enhanced with `night_hours` and `night_allowance` fields
- `AttendanceSummary` - Centralized attendance aggregation by period (daily/weekly/monthly/yearly)
- `LateNightWork` - Tracks late-night work hours (22:00-06:00) separately from overtime

**Service: `AttendanceService`**

Functions:
- `calculate_worked_hours()` - Calculate total worked hours from check-in/check-out
- `calculate_overtime_vs_night()` - Distinguish between overtime and night work
- `calculate_night_work_hours()` - Calculate hours worked in late-night period (22:00-06:00)
- `aggregate_attendance_summary()` - Aggregate comprehensive attendance data for a period
- `validate_attendance_data()` - Validate attendance data for completeness and accuracy
- `create_or_update_attendance_summary()` - Create/update centralized summary records

**API Endpoints:**
- `GET /attendance/summary-detailed/{employee_id}` - Get detailed attendance summary
- `GET /attendance/comprehensive-report` - Get comprehensive report for department
- `GET /attendance/validate/{employee_id}` - Validate attendance data
- `POST /attendance/summary/create` - Create/update attendance summary record

### 2. Paid Leave Reminder System

**Models:**
- `LeaveBalance` - Track cumulative leave balance for employees
- `LeaveReminder` - Track reminders sent to employees with acknowledgment

**Service: `LeaveReminderService`**

Functions:
- `check_leave_balance()` - Check current leave balance for an employee
- `send_reminders_to_low_balance()` - Send reminders when <3 days remaining
- `send_mid_year_reminder()` - Send mid-year leave reminders (June/July)
- `send_year_end_reminder()` - Send year-end reminders (November/December)
- `track_reminder_sent()` - Track reminder acknowledgement and actions
- `get_leave_trends()` - Analyze leave trends over multiple years
- `get_department_leave_summary()` - Get leave summary for entire department

**API Endpoints:**
- `GET /leave/balance-summary/{employee_id}` - Get leave balance for employee
- `GET /leave/trends/{employee_id}` - Analyze employee leave trends
- `POST /leave/send-reminders` - Send reminders (low_balance/mid_year/year_end)
- `POST /leave/acknowledge-reminder/{reminder_id}` - Acknowledge a reminder
- `GET /leave/department-summary/{department_id}` - Get department leave summary

### 3. Late-Night Work Hour Detection

**Detection Logic in Check-Out Endpoint:**
- Automatically detects work hours between 22:00 and 06:00
- Calculates night hours separately from regular overtime
- Applies configurable night shift allowance multiplier (default 1.5x)
- Stores in `LateNightWork` table for tracking

**Night Shift Calculation:**
- Night period: 22:00 - 06:00 (8-hour window)
- Wages: `night_hours × hourly_rate × night_shift_multiplier`
- Configurable per employee via `EmployeeWageConfig.night_shift_multiplier`

### 4. Part-Time Employee Wage Calculation

**Models:**
- `EmployeeWageConfig` - Store hourly rate and multipliers (overtime, night, holiday)
- `PayrollCycle` - Track 15-day closing and 18-day wage confirmation cycles
- `WageCalculation` - Store detailed wage calculations per cycle

**Service: `WageCalculationService`**

Functions:
- `get_or_create_wage_config()` - Create/get employee wage configuration
- `get_payroll_cycle()` - Get/create payroll cycle (automatically calculates cycle number)
- `calculate_wage_for_period()` - Calculate wages for an employee in a cycle
- `verify_and_close_cycle()` - Verify and close 15-day cycle
- `confirm_wages()` - Confirm 18-day wage cycle
- `get_wage_summary_for_employee()` - Get wage summary for date range
- `apply_wage_config_changes()` - Update employee wage configuration

**Payroll Cycle System:**
- **15-Day Closing**: Data verification and corrections (days 1-15)
- **18-Day Confirmation**: Final wage confirmation and payment approval (days 1-18)
- Each month has approximately 2 cycles (1st-15th, 16th-31st)
- Auto-calculated cycle numbers (1-24 per year)

**API Endpoints:**
- `POST /payroll/configure-employee` - Set hourly rate and allowances
- `POST /payroll/process-cycle` - Process 15-day closing cycle
- `POST /payroll/close-cycle/{cycle_id}` - Close and verify cycle
- `POST /payroll/confirm-wages/{cycle_id}` - Confirm 18-day wages
- `GET /payroll/wage-summary/{employee_id}` - Get wage summary
- `GET /payroll/employee-wages/{employee_id}` - Export wage data
- `GET /payroll/cycles` - Get list of payroll cycles

### 5. Automated Scheduled Tasks

**Scheduler: `scheduler_tasks.py`**

Jobs:
- **Daily (9:00 AM)**: Check leave balances and send reminders
  - Low balance reminders (<3 days)
  - Mid-year reminders (June/July)
  - Year-end reminders (November/December)
- **Weekly (10:00 AM on Sundays)**: Process payroll cycles
  - Auto-close cycles that have ended
  - Verify wage calculations

### 6. Comprehensive Tests

**Test Files Created:**
1. `test_leave_reminders.py` - 6 comprehensive tests for leave management
2. `test_night_work.py` - 6 tests for night work detection and attendance
3. `test_wage_calculation.py` - 6 tests for wage calculations and cycles

**Tests Cover:**
- Leave balance calculations
- Reminder sending logic
- Night work hour detection
- Overtime vs night work distinction
- Worked hours calculation
- Attendance aggregation
- Wage config management
- Payroll cycle creation
- Wage calculation accuracy
- Cycle closing and confirmation
- Wage summary generation

## Database Schema Changes

### New Tables

1. **late_night_work**
   - Tracks late-night work hours (22:00-06:00)
   - Links to employees for separate tracking from overtime

2. **leave_balance**
   - Stores cumulative leave balance per employee per year
   - Updated automatically when leaves are approved/rejected

3. **leave_reminders**
   - Tracks reminders sent to employees
   - Records acknowledgment and actions taken

4. **employee_wage_config**
   - Employee wage settings (hourly rate, multipliers)
   - Configurable per employee

5. **payroll_cycles**
   - Tracks 15-day and 18-day wage cycles
   - Stores cycle status and processing information

6. **wage_calculations**
   - Detailed wage calculations per cycle
   - Breakdown of hours, allowances, deductions
   - Tracks verification and confirmation status

7. **attendance_summary**
   - Aggregated attendance data by period
   - Centralized management of comprehensive attendance metrics

### Updated Tables

1. **attendance**
   - Added: `night_hours` (Float) - Hours worked 22:00-06:00
   - Added: `night_allowance` (Float) - Calculated night shift allowance

## Wage Calculation Formula

```
BASE WAGE = regular_hours × hourly_rate
OVERTIME WAGE = overtime_hours × hourly_rate × overtime_multiplier (default 1.5)
NIGHT SHIFT WAGE = night_hours × hourly_rate × night_shift_multiplier (default 1.5)
PAID LEAVE WAGE = paid_leave_days × 8 × hourly_rate (assumed 8-hour days)

NET WAGE = BASE WAGE + OVERTIME WAGE + NIGHT SHIFT WAGE + PAID LEAVE WAGE + ALLOWANCES - DEDUCTIONS
```

## Late-Night Work Calculation Example

**Scenario:** Employee checks in at 21:00, checks out at 07:00 (no break)

```
Total worked: 10 hours
Night period: 22:00-06:00 = 6 hours (from 22:00 to 06:00)
Regular hours: 4 hours (21:00-22:00 + 06:00-07:00)
Night hours: 6 hours (22:00-06:00)

If hourly rate = 500, night_multiplier = 1.5:
  Regular: 4 × 500 = 2,000
  Night: 6 × 500 × 1.5 = 4,500
  Total: 6,500
```

## Overtime vs Night Work Distinction

**Overtime**: Hours > scheduled hours per day (typically > 8 hours)
- Applies overtime multiplier
- Calculated as: actual_hours - scheduled_hours

**Night Work**: Hours worked between 22:00-06:00
- Applies night shift multiplier (can be different from OT multiplier)
- Calculated separately from overtime
- An employee can have BOTH overtime and night work in same day

**Example:**
- Shift: 09:00-18:00 (8 hours scheduled)
- Actual: 09:00-23:00 (14 hours, 1 hour break = 13 hours worked)
- Regular hours: 8
- Overtime: 5 hours (18:00-23:00)
- Night hours: 1 hour (22:00-23:00)
- Night wage multiplier applies to the 1 hour of night work

## Leave Reminder Rules

**Automatic Reminders:**
1. **Low Balance** - When < 3 days remaining (daily check at 9 AM)
   - Only sent once per day per employee
2. **Mid-Year** - Around June/July
   - Encourages planning for second half of year
3. **Year-End** - Around November/December
   - Reminds to use remaining days before year ends

**Reminder Tracking:**
- Each reminder is logged with date, remaining days, and type
- Employee can acknowledge reminder
- Actions taken are recorded (e.g., "Requested 2 days leave")

## Configuration & Setup

### Enable Wage Calculation for an Employee

```bash
POST /payroll/configure-employee
{
  "employee_id": 1,
  "hourly_rate": 500.0,
  "overtime_multiplier": 1.5,
  "night_shift_multiplier": 1.5
}
```

### Process Payroll Cycle

```bash
POST /payroll/process-cycle
{
  "start_date": "2025-01-01"
}
```

### Close 15-Day Cycle

```bash
POST /payroll/close-cycle/1
```

### Confirm 18-Day Wages

```bash
POST /payroll/confirm-wages/1
```

## Performance Considerations

1. **Attendance Aggregation**: Uses efficient SQL queries with proper indexing
2. **Leave Balance**: Cached in LeaveBalance table, updated on leave approval
3. **Wage Calculations**: Precomputed during cycle processing
4. **Scheduled Tasks**: Run asynchronously without blocking API
5. **Database Indexes**: Created on frequently queried fields (date, employee_id, status)

## Error Handling

**Validation Checks:**
- Hourly rate must be > 0 before wage calculation
- Attendance records must have valid check-in/out times
- Payroll cycles must be closed before confirmation
- Leave dates must not overlap for same leave type

**Error Messages:**
- Clear, actionable error messages returned in API responses
- Validation errors logged for audit trail
- Graceful handling of edge cases (negative wages, invalid dates, etc.)

## Future Enhancements

1. Export wage reports to Excel with detailed breakdowns
2. Support for different wage periods (weekly, biweekly, monthly)
3. Configurable leave year boundaries (not just calendar year)
4. Tax and deduction calculations integration
5. Multi-currency support for international teams
6. Bulk wage confirmation for multiple employees
7. Historical wage tracking and comparison
8. Employee wage slip generation

## Testing

Run comprehensive tests:

```bash
# Night work and attendance tests
python test_night_work.py

# Leave reminder tests
python test_leave_reminders.py

# Wage calculation tests
python test_wage_calculation.py
```

All tests include:
- Correct calculation verification
- Edge case handling
- Error condition testing
- Data consistency checks
