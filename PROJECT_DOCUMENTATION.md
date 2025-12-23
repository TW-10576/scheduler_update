# Factory Shift Scheduling and Attendance Management System
## Complete Technical Documentation

---

## 1. Project Overview

### 1.1 Problem Statement
The Factory Shift Scheduling and Attendance Management System solves the challenge of coordinating complex factory operations where:
- Multiple shifts must be scheduled across different departments and roles
- Employee attendance must be tracked with precision, including overtime and night work
- Leave requests must be managed with balance tracking and approval workflows
- Wage calculations must account for different types of work (regular, overtime, night shifts)
- Managers need visibility into departmental operations while maintaining role-based access control

### 1.2 Target Users
- **Factory Management**: Administrators managing the entire system, creating departments and managers
- **Department Managers**: Managing employees within their department, creating schedules, approving leave and overtime
- **Factory Employees**: Self-service portal for checking in/out, requesting leave, viewing schedules, requesting overtime

### 1.3 System Capabilities
The system provides:
- Multi-role access control (Admin, Manager, Employee)
- Complete shift scheduling and planning
- Real-time check-in/check-out tracking
- Comprehensive attendance recording with night work detection
- Leave management with balance tracking and approval workflows
- Overtime request and approval system
- Part-time wage calculation with 15-day cycles and 18-day confirmation
- Automated scheduled tasks (daily leave reminders, weekly payroll processing)
- Department and employee management
- Messaging and notification systems

---

## 2. System Architecture

### 2.1 High-Level Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                      Web Browser / Client                     │
├─────────────────────────────────────────────────────────────┤
│                          HTTPS / HTTP                        │
├─────────────────────────────────────────────────────────────┤
│              Frontend (React + Vite + Tailwind)              │
│  - Login/Authentication                                      │
│  - Employee Dashboard (Check-in, Schedule, Leave, Overtime)  │
│  - Manager Dashboard (Schedules, Approvals, Attendance)      │
│  - Admin Dashboard (System Management, Reports)              │
├─────────────────────────────────────────────────────────────┤
│                    HTTP / JSON API                           │
├─────────────────────────────────────────────────────────────┤
│           Backend API (FastAPI + Python 3.11)                │
│  - Authentication (JWT Tokens)                               │
│  - RESTful Endpoints (90+ endpoints)                          │
│  - Business Logic Services                                   │
│  - Scheduled Task Execution                                  │
├─────────────────────────────────────────────────────────────┤
│              Async Database Access (SQLAlchemy)              │
├─────────────────────────────────────────────────────────────┤
│         PostgreSQL 15 (Database + Data Storage)              │
│  - 15+ Tables (Normalized relational schema)                 │
│  - Cascading relationships and constraints                   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

**Frontend:**
- React 18 - UI component framework
- Vite 5 - Build tool and dev server
- Tailwind CSS 3 - Utility-first CSS framework
- React Router 6 - Client-side routing
- Axios - HTTP client for API communication
- Lucide Icons - Icon library
- Date-fns - Date manipulation utility

**Backend:**
- FastAPI - Asynchronous web framework
- Python 3.11 - Runtime environment
- SQLAlchemy 2.0 - Async ORM for database operations
- Asyncpg - PostgreSQL async driver
- Python-Jose - JWT token management
- Passlib/Argon2 - Password hashing and verification
- APScheduler - Scheduled task execution
- OR-Tools - Constraint-based schedule optimization
- Openpyxl - Excel file generation for exports
- Pydantic - Data validation and serialization

**Database:**
- PostgreSQL 15 - Relational database management system

**Infrastructure:**
- Docker & Docker Compose - Containerization and orchestration
- WSL (Windows Subsystem for Linux) - Development environment

### 2.3 Component Communication

1. **Client-to-Server**: React components communicate with FastAPI backend via HTTP/HTTPS using Axios
2. **Authentication Flow**: JWT tokens stored in localStorage, sent with each API request via Authorization header
3. **Database Access**: Backend uses SQLAlchemy async ORM to communicate with PostgreSQL
4. **Scheduled Tasks**: APScheduler runs background jobs (leave reminders, payroll processing) independently
5. **Data Validation**: Pydantic schemas validate data at API boundaries before database operations

---

## 3. Frontend Implementation

### 3.1 Technology Stack
- **Framework**: React 18 with functional components and hooks
- **Build System**: Vite 5 (dev server at http://localhost:5173 during development)
- **Styling**: Tailwind CSS 3 (utility classes for responsive design)
- **Routing**: React Router v6 (declarative route configuration)
- **HTTP Client**: Axios (with interceptor support for token attachment)
- **Icons**: Lucide React (SVG icons)

### 3.2 Project Structure

```
frontend/
├── src/
│   ├── App.jsx                          # Main router configuration
│   ├── main.jsx                         # React entry point
│   ├── index.css                        # Global styles
│   ├── pages/
│   │   ├── Login.jsx                    # Login form and authentication
│   │   ├── Employee.jsx                 # Employee dashboard
│   │   ├── Manager.jsx                  # Manager dashboard
│   │   └── Admin.jsx                    # Admin dashboard
│   ├── components/
│   │   ├── AttendanceTracker.jsx        # Check-in/out tracking
│   │   ├── CheckInOut.jsx               # Check-in/out UI component
│   │   ├── EmployeeScheduleView.jsx     # Employee schedule display
│   │   ├── LeaveManagement.jsx          # Leave request form and status
│   │   ├── ManagerScheduleView.jsx      # Manager schedule view and editing
│   │   ├── OvertimeApproval.jsx         # Overtime approval interface
│   │   ├── OvertimeRequest.jsx          # Overtime request form
│   │   ├── RoleManagement.jsx           # Role CRUD operations
│   │   ├── ScheduleCalendarView.jsx     # Calendar-based schedule view
│   │   ├── ScheduleGenerator.jsx        # Schedule generation interface
│   │   ├── ScheduleManager.jsx          # Schedule CRUD operations
│   │   ├── ShiftAssignmentWithDragDrop.jsx # Drag-drop shift assignment
│   │   ├── ShiftManagement.jsx          # Shift CRUD operations
│   │   ├── common/                      # Reusable UI components
│   │   └── layout/                      # Layout components (header, sidebar)
│   ├── services/
│   │   └── api.js                       # Centralized API client with interceptors
│   └── utils/
│       └── [utility functions]
├── index.html                           # HTML entry point
├── package.json                         # Dependencies and scripts
├── vite.config.js                       # Vite configuration
├── tailwind.config.js                   # Tailwind CSS configuration
└── postcss.config.js                    # PostCSS configuration
```

### 3.3 Main UI Pages and Their Purpose

#### Login Page (`Login.jsx`)
- User authentication entry point
- Accepts username and password
- Sends credentials to `/token` endpoint for JWT token
- Stores token and user data in localStorage
- Redirects to appropriate dashboard based on user role

#### Employee Dashboard (`Employee.jsx`)
- **Check-In/Out Interface**: Real-time check-in and check-out with status indicators
- **Personal Schedule**: View upcoming shifts assigned to the employee
- **Leave Management**: 
  - Request leave with date selection
  - View leave balance
  - Track leave request status
- **Overtime Management**:
  - Request overtime hours
  - View overtime status and approvals
- **Attendance History**: View past attendance records and work hours

#### Manager Dashboard (`Manager.jsx`)
- **Department Overview**: Summary of assigned department's operations
- **Employee Management**: View, add, edit, and delete employees in department
- **Role Management**: Create and manage job roles with shift types
- **Shift Management**: Define shift templates with timing and capacity constraints
- **Schedule Management**:
  - View department schedules
  - Generate optimized schedules with constraint solver
  - Manually assign shifts to employees
  - Edit and delete schedule entries
- **Attendance Tracking**: View employee attendance records with worked hours
- **Approval Interface**: Approve/reject leave and overtime requests from team members
- **Reports**: Generate monthly and weekly attendance reports

#### Admin Dashboard (`Admin.jsx`)
- **System Management**: Create and manage users (admin, manager, employee)
- **Department Management**: Create departments and assign managers
- **Manager Assignment**: Assign managers to departments
- **Global Attendance Reports**: Company-wide attendance analytics
- **Export Functionality**: Export attendance data to Excel
- **System Configuration**: Manage system-wide settings and constraints

### 3.4 Authentication on Frontend

**Token-Based Authentication Flow:**
1. User submits login credentials (username/password)
2. Frontend sends POST request to `/token` endpoint
3. Backend validates credentials and returns JWT access token
4. Frontend stores token in `localStorage` under key `token`
5. Frontend stores user data in `localStorage` under key `user`
6. For subsequent API requests, Axios interceptor attaches token in `Authorization: Bearer <token>` header
7. Backend validates token and identifies current user for each request
8. If token expired, backend returns 401, frontend redirects to login page

**Token Details:**
- **Algorithm**: HS256 (HMAC SHA-256)
- **Secret Key**: Configured in `backend/app/config.py` (SECRET_KEY)
- **Expiration**: 24 hours (1440 minutes)
- **Payload**: Contains username and expiration timestamp

**Session Management:**
- Tokens stored in browser localStorage (persists across page refreshes)
- Logout clears localStorage, removing token and user data
- Role-based route protection redirects unauthorized users

---

## 4. Backend Implementation

### 4.1 FastAPI Application Structure

The backend is organized as a single FastAPI application (`app/main.py`) with supporting modules:

```
backend/
├── app/
│   ├── __init__.py                      # Package initialization
│   ├── main.py                          # FastAPI app with 90+ endpoints
│   ├── models.py                        # SQLAlchemy database models (15 tables)
│   ├── schemas.py                       # Pydantic request/response schemas
│   ├── config.py                        # Configuration settings
│   ├── database.py                      # Database connection and session management
│   ├── auth.py                          # Authentication utilities and JWT handling
│   ├── helpers.py                       # Reusable business logic functions
│   ├── attendance_service.py            # Attendance calculation and aggregation
│   ├── leave_reminder_service.py        # Leave balance tracking and reminders
│   ├── wage_calculation_service.py      # Wage calculation and payroll processing
│   ├── schedule_generator.py            # Priority-based schedule optimization
│   ├── scheduler.py                     # APScheduler setup and configuration
│   └── scheduler_tasks.py               # Scheduled job definitions
├── init_db.py                           # Database initialization script
├── run.py                               # Application entry point
├── requirements.txt                     # Python package dependencies
├── Dockerfile                           # Container configuration
└── [test files]                         # API and integration tests
```

### 4.2 API Modules and Responsibilities

**Main Application (`main.py`)**
- FastAPI app instance with CORS middleware
- 90+ endpoints organized by feature:
  - Authentication (1 endpoint)
  - User management (3 endpoints)
  - Department management (5 endpoints)
  - Manager management (4 endpoints)
  - Employee management (4 endpoints)
  - Role management (4 endpoints)
  - Shift management (4 endpoints)
  - Schedule management (6 endpoints)
  - Check-in/Check-out (2 endpoints)
  - Attendance tracking (8 endpoints)
  - Leave management (5 endpoints)
  - Leave statistics (2 endpoints)
  - Messaging (4 endpoints)
  - Notifications (4 endpoints)
  - Unavailability management (3 endpoints)
  - Overtime management (7 endpoints)
  - Leave reminders (3 endpoints)
  - Payroll and wage calculation (7 endpoints)

**Database Models (`models.py`)**
Defines 15 tables with relationships:

Core Tables:
- `User` - Authentication accounts (admin, manager, employee)
- `Department` - Organizational units managed by managers
- `Manager` - Links User to Department
- `Employee` - Staff records with role and department assignment

Operational Tables:
- `Role` - Job positions/types (Engineer, Technician, etc.)
- `Shift` - Shift templates with timing and capacity (Morning Shift 5-2, Evening Shift 2-11)
- `Schedule` - Individual shift assignments to employees on specific dates

Leave and Time-Off Tables:
- `LeaveRequest` - Leave requests with approval workflow
- `LeaveBalance` - Cumulative leave balance tracking per employee per year
- `LeaveReminder` - Reminders sent when balance is low
- `Unavailability` - Employee unavailability constraints (sick, training, etc.)

Attendance and Work Hours Tables:
- `CheckInOut` - Raw check-in and check-out records with timestamps
- `Attendance` - Processed attendance records with calculated hours
- `LateNightWork` - Separate tracking for night work (22:00-06:00)
- `OvertimeWorked` - Daily overtime hours tracking
- `OvertimeTracking` - Monthly overtime allocation and balance
- `OvertimeRequest` - Employee overtime requests with approval workflow

Wage and Payroll Tables:
- `EmployeeWageConfig` - Hourly rates and payment multipliers per employee
- `PayrollCycle` - 15-day closing and 18-day confirmation cycles
- `WageCalculation` - Detailed wage calculations per cycle
- `AttendanceSummary` - Aggregated attendance data by period

Messaging:
- `Message` - User-to-user or department-wide messages
- `Notification` - System notifications for approvals and events

**Authentication Module (`auth.py`)**
- `get_password_hash()` - Hash passwords using Argon2
- `verify_password()` - Verify password against hash
- `create_access_token()` - Generate JWT tokens
- `get_current_user()` - Dependency to get authenticated user from token
- `get_current_active_user()` - Ensure user is active
- `require_admin()` - Role-based access control for admin endpoints
- `require_manager()` - Role-based access control for manager endpoints
- `require_employee()` - Role-based access control for employee endpoints

**Helpers Module (`helpers.py`)**
Reusable business logic functions:
- `calculate_leave_days()` - Calculate days between dates, handle half-days
- `get_leave_balance()` - Get/create LeaveBalance record
- `deduct_leave_balance()` - Deduct days from balance with validation
- `create_notification()` - Create notification records
- `check_and_send_low_balance_notification()` - Alert on low balance
- `is_employee_on_approved_leave()` - Check leave status for date
- `get_manager_department()` - Get manager's assigned department

**Service Modules:**

*AttendanceService (`attendance_service.py`)*
- `calculate_worked_hours()` - Calculate total worked hours from check-in/check-out
- `calculate_overtime_vs_night()` - Distinguish overtime from night work
- `calculate_night_work_hours()` - Calculate hours 22:00-06:00
- `aggregate_attendance_summary()` - Aggregate data by period
- `validate_attendance_data()` - Validate completeness and accuracy
- `create_or_update_attendance_summary()` - Create/update summary records

*LeaveReminderService (`leave_reminder_service.py`)*
- `check_leave_balance()` - Get current balance
- `send_reminders_to_low_balance()` - Send alerts when <3 days
- `send_mid_year_reminder()` - June/July mid-year reminder
- `send_year_end_reminder()` - November/December end-year reminder
- `track_reminder_sent()` - Track acknowledgment
- `get_leave_trends()` - Analyze trends over years
- `get_department_leave_summary()` - Department-level summary

*WageCalculationService (`wage_calculation_service.py`)*
- `get_or_create_wage_config()` - Create/get employee config
- `get_payroll_cycle()` - Get/create cycle (auto-calculate number)
- `calculate_wage_for_period()` - Calculate wages for cycle
- `verify_and_close_cycle()` - Verify 15-day closing
- `confirm_wages()` - Confirm 18-day wages
- `get_wage_summary_for_employee()` - Get summary for date range
- `apply_wage_config_changes()` - Update configuration

*ScheduleGenerator (`schedule_generator.py`)*
Uses Google OR-Tools CP-SAT solver:
- Priority-based distribution of shifts across roles
- Load balancing across employees
- Constraint satisfaction for:
  - Employee availability (leave, unavailability)
  - Shift capacity limits (min/max employees per shift)
  - Employee shift quotas (shifts per week)
  - Role priority percentages
- Handles unavailability with reassignment to alternative days

### 4.3 Authentication and Authorization Logic

**Authentication Flow:**
1. POST `/token` accepts username and password
2. Query database for User with matching username
3. Verify password using `verify_password()` function
4. If valid, create JWT token with 24-hour expiration
5. Return token and user information to client

**Authorization Flow:**
1. Client includes token in `Authorization: Bearer <token>` header
2. `get_current_user()` dependency extracts and validates token
3. JWT payload decoded and username extracted
4. User queried from database to ensure still active
5. Role-based dependencies (`require_admin`, `require_manager`) check user_type
6. If check fails, return 403 Forbidden error

**Session Management:**
- No server-side session storage
- Pure JWT-based stateless authentication
- Token expiration enforced client-side (24 hours)
- Logout by removing token from localStorage

### 4.4 Error Handling Approach

**HTTP Status Codes:**
- `200 OK` - Successful GET/POST/PUT/DELETE
- `201 Created` - Resource created successfully
- `400 Bad Request` - Validation error or invalid input
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Authenticated but lacking permissions
- `404 Not Found` - Resource does not exist
- `422 Unprocessable Entity` - Pydantic validation failed
- `500 Internal Server Error` - Unexpected server error

**Error Response Format:**
```json
{
  "detail": "Error description or Pydantic validation details"
}
```

**Custom Exception Handler:**
- HTTPException handler adds CORS headers to error responses
- Ensures error responses work in browser environments

**Validation:**
- Pydantic schemas validate request data before processing
- Database uniqueness constraints enforce data integrity
- Foreign key constraints prevent orphaned records
- Manual validation checks for business logic (e.g., leave balance)

---

## 5. Database Design

### 5.1 Main Tables and Relationships

**User Hierarchy:**
```
User (1) ──→ (1) Manager ──→ (1) Department
                               ↓
                         (N) Employee
```

**Operational Structure:**
```
Department (1) ──→ (N) Role ──→ (N) Shift
                      ↓
                 (N) Employee
                      ↓
                 (N) Schedule (date/role/shift assignment)
```

**Leave Management:**
```
Employee (1) ──→ (N) LeaveRequest
          ↓
     (1) LeaveBalance (per year)
          ↓
     (N) LeaveReminder
```

**Overtime Management:**
```
Employee (1) ──→ (N) OvertimeRequest
          ↓
     (1) OvertimeTracking (monthly)
          ↓
     (N) OvertimeWorked
```

**Attendance and Wages:**
```
Employee (1) ──→ (N) Schedule ──→ (1) CheckInOut
          ↓                            ↓
    (N) Attendance ←─────────────────┘
          ↓
    (1) AttendanceSummary
          ↓
    (1) EmployeeWageConfig
          ↓
    (N) WageCalculation → PayrollCycle
```

### 5.2 How Data is Stored

**User and Access Control:**
- Users stored in `users` table with hashed passwords
- Managers linked to Users via `managers` table (one-to-one)
- Employees can optionally link to Users for self-service login
- Three user types: admin, manager, employee

**Shift Scheduling:**
- Roles created per department (Engineer, Technician, etc.)
- Shifts created per role with timing and capacity (Morning 5-2, Evening 2-11)
- Schedules assign specific shifts to employees on specific dates
- Schedule can optionally link to a Shift template or have custom times

**Attendance Tracking:**
1. Employee checks in/out via mobile app or web interface
2. CheckInOut record created with timestamp
3. On check-out, Attendance record created with:
   - Worked hours (calculated from check-in to check-out)
   - Overtime hours (if >8 hours per day)
   - Night hours (if between 22:00-06:00)
   - Status (on time, late, very late, etc.)
4. LateNightWork record created separately for night shifts
5. AttendanceSummary aggregated by period (daily/weekly/monthly/yearly)

**Leave Management:**
1. Employee creates LeaveRequest (start_date, end_date, leave_type)
2. Manager approves or rejects request
3. If approved:
   - LeaveBalance updated (used_paid_leave increased, remaining decreased)
   - Notification sent to employee
   - Schedules for those dates marked as 'leave'
   - Attendance records show status='leave'

**Overtime Management:**
1. Employee requests overtime via OvertimeRequest
2. Manager approves or rejects
3. If approved, hours added to OvertimeTracking for that month
4. When employee works overtime hours recorded in OvertimeWorked

**Wage Calculation:**
1. EmployeeWageConfig stores hourly rate and multipliers
2. For each PayrollCycle (15-day period):
   - WageCalculation created with breakdown of:
     - Regular hours × hourly rate
     - Overtime hours × hourly rate × overtime_multiplier
     - Night hours × hourly rate × night_shift_multiplier
     - Leave hours (paid_leave × 8 × hourly rate)
   - 15-day closing: Manager/admin verifies data
   - 18-day confirmation: Final wage approval
3. Payment tracked in WageCalculation.is_paid and payment_date

### 5.3 Important Constraints and Validations

**Database Constraints:**
- Primary keys (id) indexed for fast lookup
- Foreign keys enforce referential integrity (cascade on delete)
- Unique constraints on:
  - `users.username`, `users.email`
  - `employees.employee_id`, `employees.email`
  - `departments.dept_id`
  - `employees.user_id` (optional, one employee per user max)

**Business Logic Validations:**
- Leave balance cannot go negative (validated before approval)
- Employee cannot check in twice on same day
- Employee cannot be assigned to multiple roles
- Shift start_time must be before end_time
- Employee cannot request leave in past
- Leave request end_date must be >= start_date
- Overtime hours must be positive
- Hourly rate must be positive (wage config)

**Data Integrity:**
- CheckInOut linked to Schedule (employee presence verification)
- Attendance linked to Schedule (who was assigned that day)
- LeaveBalance updated only on approved leave
- OvertimeTracking updated only on approved requests
- WageCalculation linked to PayrollCycle for tracking

---

## 6. Core Business Logic

### 6.1 Shift Scheduling Logic

**Schedule Generation Process:**

The system uses a priority-based distribution algorithm with Google OR-Tools CP-SAT solver:

1. **Input Phase:**
   - Specify date range (e.g., 2024-01-01 to 2024-01-31)
   - System loads employees, roles, shifts, leaves, and unavailability

2. **Capacity Calculation:**
   - For each role, calculate total shifts needed:
     - Base: (sum of employees × shifts_per_week × weeks_in_period)
     - Minus: leave days (hard block - no reassignment)
     - Unavailable slots noted but reassigned to alternative days

3. **Priority Distribution:**
   - Allocate shifts to each shift type based on priority_percentage:
     - If Role has priority_percentage=60, 60% of role's shifts go to priority shift
     - Remaining 40% distributed to other shifts
   - Use largest-remainder method for fractional allocation

4. **Date Distribution:**
   - Distribute shift allocations across calendar days
   - Consider day_priority for each day (some days may need more coverage)

5. **Employee Assignment:**
   - Use OR-Tools CP-SAT solver with constraints:
     - Each employee gets approximately equal shifts
     - Employee cannot work on leave dates
     - Employee cannot work on unavailable dates (reassigned to alternative)
     - Shift capacity limits (min/max employees per shift)
     - Employee shift quota (shifts_per_week)

6. **Output:**
   - Schedule records created in database
   - One Schedule per employee per date per role/shift
   - Schedule linked to Shift template if applicable
   - Includes start_time/end_time from shift template

**Constraint Handling:**
- **Leave Dates**: Hard block - employee skipped for that date
- **Unavailable Dates**: Employee reassigned to another day (same week if possible)
- **Shift Capacity**: min_emp and max_emp enforced
- **Weekend Requirements**: weekend_required flag in Role
- **Break Times**: break_minutes from Role applied to schedules

### 6.2 Attendance Recording (Check-in / Check-out)

**Check-In Process:**
1. Employee initiates check-in via mobile/web app
2. System records:
   - Employee ID
   - Current timestamp
   - Location (optional)
   - Status: on-time (if before shift start), late, very-late

**Check-Out Process:**
1. Employee initiates check-out
2. System records check-out timestamp
3. Calculates:
   - Total worked hours = (check-out_time - check-in_time) - break_minutes
   - Overtime hours = max(0, worked_hours - 8)
   - Night hours = hours between 22:00-06:00
   - Checks if employee on approved leave for that day
4. Creates/updates Attendance record with:
   - in_time, out_time
   - status (on-time, late, very-late, missed)
   - worked_hours, overtime_hours, night_hours
   - break_minutes (from role or schedule)
5. Creates LateNightWork record if night_hours > 0
6. Updates/creates OvertimeWorked record if overtime_hours > 0
7. Sends notification to employee

**Night Work Detection Logic:**
- Night period: 22:00 to 06:00 (next day)
- If check-in at 21:00 and check-out at 07:00:
  - Total worked: 10 hours
  - Night hours: 6 hours (22:00-06:00)
  - Regular hours: 4 hours
- Night allowance calculated: night_hours × hourly_rate × night_shift_multiplier

### 6.3 Role-Based Access Control

**Three Role Levels:**

**Admin (user_type='admin')**
- Manage all users (create, delete, deactivate)
- Create departments
- Assign managers to departments
- View all department schedules and attendance
- Generate company-wide reports
- Cannot approve leaves/overtime (manager function)
- Cannot perform employee operations (check-in/out)

**Manager (user_type='manager')**
- Assigned to one department via Manager record
- Manage employees within their department:
  - Add/edit/delete employees
  - View employee schedules and attendance
- Create roles and shifts within their department
- Generate department schedules
- Approve/reject leave requests from team members
- Approve/reject overtime requests
- Generate department reports
- Cannot manage other departments' data
- Cannot access admin functions

**Employee (user_type='employee')**
- Can only perform self-service operations:
  - Check in/out
  - View personal schedule
  - Request leave
  - Request overtime
  - View personal attendance history
- Cannot access other employees' data
- Cannot access management functions

**Endpoint Authorization Pattern:**
```python
async def endpoint(
    current_user: User = Depends(get_current_active_user),  # All authenticated users
    # OR
    current_user: User = Depends(require_manager),          # Managers and admins only
    # OR
    current_user: User = Depends(require_admin),            # Admins only
):
    # Additional checks if needed (e.g., user's department)
    pass
```

### 6.4 Manager vs Employee Behavior

**Schedule Management:**
- **Employee**: View personal schedule (GET /schedules filtered to self)
- **Manager**: View department schedules, create/edit/delete schedules

**Attendance:**
- **Employee**: View personal attendance history
- **Manager**: View all employee attendance in department, see daily stats

**Leave Management:**
- **Employee**: 
  - Request leave (POST /leave-requests)
  - View personal balance (GET /leave/balance-summary/{self})
  - View personal requests
- **Manager**: 
  - Approve/reject team member requests (PUT /leave-requests/{id}/approve)
  - View team leave summary
  - See leave trends

**Overtime:**
- **Employee**:
  - Request overtime (POST /overtime-requests)
  - View personal overtime balance
- **Manager**:
  - Approve/reject team overtime (PUT /overtime-requests/{id}/approve)
  - View team overtime tracking
  - Check overtime availability

**Department Data:**
- **Employee**: Cannot access department-level data
- **Manager**: Full access to department data (employees, schedules, attendance, reports)

---

## 7. Current Features Implemented

### 7.1 Authentication and User Management
- JWT token-based authentication with 24-hour expiration
- Password hashing with Argon2
- User creation with role assignment (admin, manager, employee)
- User deactivation (soft delete)
- Role-based endpoint access control

### 7.2 Department Management
- Create departments with 3-digit auto-generated IDs
- Update department information
- Assign managers to departments (one-to-one relationship)
- Soft delete departments (is_active flag)
- View department details with employee count

### 7.3 Employee Management
- Create employees with:
  - 5-digit employee ID (e.g., "00001")
  - Name, email, phone, address
  - Department assignment
  - Role assignment
  - Weekly shift quota
  - Paid leave allocation per year
- Update employee information
- Soft delete employees
- View employee list by department
- Export employee data

### 7.4 Role and Shift Management
- Create roles (positions) per department with:
  - Description
  - Priority percentage
  - Required skills
  - Break duration
  - Weekend requirement
  - Schedule configuration
- Create shifts under roles with:
  - Name and timing (start_time, end_time)
  - Priority level
  - Min/max employee capacity
  - Schedule configuration
- Edit and delete roles/shifts
- Retrieve roles with associated shifts

### 7.5 Schedule Management
- Generate schedules using priority-based optimization algorithm
- Manually create schedules with drag-drop interface
- Link schedules to shift templates (or use custom times)
- Update schedules and mark as completed/missed/cancelled
- Delete schedules
- View schedules by employee, date range, or department
- Conflict detection (prevent double scheduling)
- Export schedules to Excel

### 7.6 Check-In/Check-Out System
- Real-time check-in with automatic status (on-time, late, very-late)
- Real-time check-out with worked hours calculation
- Break time deduction
- Night work detection (22:00-06:00)
- Overtime calculation (hours > 8 per day)
- Location tracking (optional)
- Check-in history and status updates

### 7.7 Attendance Tracking
- Attendance record creation on check-out
- Detailed attendance summaries:
  - Daily, weekly, monthly, yearly aggregation
  - Total hours, regular hours, overtime hours, night hours
  - Leave days, paid leave, unpaid leave
  - On-time percentage and lateness tracking
- Manager and admin attendance views
- Export attendance data (monthly, weekly, employee-specific)
- Attendance validation and data consistency checks
- Night work calculation separate from overtime

### 7.8 Leave Management
- Leave request creation with date range and type
- Leave types: paid, unpaid, sick, compensatory, half-day
- Leave approval workflow with manager review
- Leave rejection with notes
- Leave balance tracking:
  - Annual paid leave allocation (10 days default)
  - Track used and remaining
  - Prevent negative balance (validation)
- Leave history and status visibility
- Leave statistics by employee and department

### 7.9 Leave Reminders and Balance Tracking
- Automatic leave balance calculation
- Low balance reminders (when <3 days remaining)
- Mid-year reminders (June/July)
- Year-end reminders (November/December)
- Reminder acknowledgment tracking
- Leave trend analysis (3-year comparison)
- Department leave summary reports

### 7.10 Overtime Management
- Overtime request creation with hours and reason
- Overtime approval workflow
- Monthly overtime allocation tracking
- Overtime balance checking (prevent over-allocation)
- Overtime worked recording and tracking
- Overtime statistics and reports

### 7.11 Wage and Payroll System
- Employee wage configuration:
  - Hourly rate
  - Overtime multiplier (default 1.5x)
  - Night shift multiplier (default 1.5x)
  - Holiday multiplier (default 2.0x)
  - Part-time vs full-time designation
- Payroll cycle management:
  - 15-day cycles with 6 cycles per month
  - Auto-calculated cycle numbers (1-24 per year)
  - 15-day closing: Data verification
  - 18-day confirmation: Wage approval
- Wage calculations:
  - Regular wages = regular_hours × hourly_rate
  - Overtime wages = overtime_hours × hourly_rate × overtime_multiplier
  - Night shift wages = night_hours × hourly_rate × night_shift_multiplier
  - Paid leave wages = paid_leave_days × 8 × hourly_rate
- Wage summary and export
- Payment status tracking

### 7.12 Messaging System
- User-to-user direct messaging
- Department-wide announcements
- Message read/unread status
- Message deletion (soft delete)
- Message history

### 7.13 Notifications
- System notifications for:
  - Leave request approvals/rejections
  - Overtime approvals/rejections
  - Low leave balance alerts
  - Schedule changes
- Notification read/unread status
- Mark all notifications as read
- Delete notifications

### 7.14 Scheduled Tasks (Background Jobs)
- **Daily at 9:00 AM**: Leave balance reminders
  - Low balance (<3 days)
  - Mid-year (June/July)
  - Year-end (November/December)
- **Weekly at 10:00 AM on Sundays**: Payroll processing
  - Auto-close ended cycles
  - Verify wage calculations

### 7.15 Data Export
- Export attendance (monthly format with employee summary)
- Export attendance (weekly format with daily breakdown)
- Export attendance (employee-specific monthly)
- Export generates Excel files with:
  - Formatted headers
  - Conditional formatting for status
  - Summary statistics
  - Department-level aggregation

### 7.16 Unavailability Management
- Mark employee unavailability (sick, training, personal, etc.)
- Unavailability dates prevent schedule assignment
- Unavailability reason tracking
- Soft delete unavailability records

---

## 8. Known Limitations and Issues

### 8.1 Technical Limitations
1. **Session Management**: No server-side session refresh mechanism. Token lasts 24 hours with no refresh token implementation. Long-lived operations may require re-login.

2. **Real-Time Updates**: System lacks WebSocket support. UI updates require manual refresh to see changes made by other users.

3. **Schedule Generator**: OR-Tools constraint solver may timeout on very large datasets (1000+ employees). Performance not tested at enterprise scale.

4. **Concurrent Check-Ins**: Multiple simultaneous check-ins from same employee not prevented at application level (only at UI level). Database could allow duplicate CheckInOut records.

5. **Timezone Handling**: System assumes all times in local timezone. No timezone conversion or multi-timezone support.

6. **Data Storage**: Night work times stored in separate LateNightWork table but also in Attendance.night_hours. Potential data duplication and inconsistency risk.

### 8.2 Incomplete Features
1. **Leave Type Distinctions**: Model supports paid/unpaid/sick/compensatory but approval workflow treats all equally. No differential rules based on type.

2. **Shift Swapping**: No employee-to-employee shift swap mechanism. Employees cannot request shift trades.

3. **Department Hierarchy**: System only supports single-level departments. No sub-departments or hierarchical structures.

4. **Approval Chain**: All approvals go to single manager. No escalation or multi-level approval workflows.

5. **Bulk Operations**: No bulk employee import, bulk schedule creation, or bulk leave approval.

6. **Audit Trail**: Changes to schedules, leaves, and settings not logged. No audit trail of who changed what and when.

7. **Backup and Recovery**: No automated backup strategy documented. Manual database backups required.

### 8.3 Known Bugs
1. **Schedule Conflicts on Reassignment**: When unavailable employee reassigned by schedule generator, original schedule not deleted, creating duplicates.

2. **Leave Balance Edge Cases**: Half-day leave calculations may not correctly update balance if same day partially scheduled twice.

3. **Overtime Carry-Over**: Monthly overtime resets without carrying over unused hours to next month.

4. **Night Work Edge Cases**: If employee checks out after midnight, night hours calculation may double-count (appears in both days). Should span only single night period.

5. **Export Formatting**: Excel exports may lose formatting if opened in non-English locale systems.

### 8.4 Performance Concerns
1. **Query N+1 Problem**: Many endpoints may not use eager loading (selectinload), causing multiple queries for related objects.

2. **Large Attendance Exports**: Exporting 1000+ employee records monthly may timeout or exhaust memory.

3. **Schedule Generation**: Large departments (200+ employees) may see slow schedule generation.

4. **Notification Polling**: Frontend polls notifications every 30 seconds. Real-time updates not batched.

### 8.5 Security Considerations (Non-Production Ready)
1. **Default Credentials**: Demo includes hardcoded test users (admin/admin123, manager1/manager123, etc.)

2. **SECRET_KEY Hardcoded**: JWT secret key in config.py is static. Must be changed in production via environment variables.

3. **CORS Wide Open**: CORS allows multiple origins including localhost:*. Production should restrict to specific domain.

4. **Password Requirements**: No password strength validation. Test passwords very simple (admin123).

5. **Input Validation**: Some endpoints lack comprehensive input validation (e.g., negative hours accepted).

6. **Rate Limiting**: No rate limiting on endpoints. Brute-force attacks possible on login.

7. **HTTPS**: System runs on HTTP only. No encryption in transit for demo. Production requires HTTPS.

---

## 9. Future Enhancements (Suggested)

### 9.1 Authentication and Security (Priority: High)
- **Refresh Token Implementation**: Add refresh tokens to extend sessions without re-login
- **Password Reset Flow**: Self-service password reset via email
- **Two-Factor Authentication (2FA)**: Email or SMS-based 2FA for managers/admins
- **Audit Trail**: Log all changes with user, timestamp, and action
- **Rate Limiting**: Implement exponential backoff on failed login attempts
- **API Key Authentication**: Allow backend-to-backend API integration with keys

### 9.2 Advanced Scheduling (Priority: High)
- **Shift Swapping**: Allow employees to request shift trades
- **Recurring Patterns**: Define recurring schedules (e.g., "same shift every Tuesday")
- **Multi-Shift Scheduling**: Allow employee to work multiple shifts per day
- **Circular Roster**: Automatic rotating shift patterns (morning → evening → night)
- **Constraint Improvements**: Add skill-based assignment, employee preferences
- **Conflict Resolution**: Automated conflict detection and resolution UI

### 9.3 Advanced Leave Management (Priority: Medium)
- **Leave Types with Rules**: Differential rules for sick vs vacation leave
- **Maternity/Paternity Leave**: Special extended leave with specific rules
- **Carryover Handling**: Rollover unused leave to next year with caps
- **Leave Calendar**: Visual calendar showing all leaves
- **Buddy Coverage**: Assign buddy employee for coverage during leave
- **Leave Accrual**: Automatic leave accrual based on tenure

### 9.4 Real-Time Communication (Priority: Medium)
- **WebSocket Support**: Real-time notifications and schedule updates
- **In-App Chat**: Direct messaging between employees and managers
- **Announcement Broadcasts**: Instant broadcasts to all departments
- **Push Notifications**: Mobile push for approvals and schedule changes
- **Escalation Alerts**: Urgent notifications for critical events

### 9.5 Mobile Application (Priority: Medium)
- **Native Mobile App**: iOS/Android app for check-in/check-out
- **Offline Mode**: Continue check-in/out without internet connection
- **Biometric Login**: Fingerprint or face recognition
- **GPS Tracking**: Location-based check-in (geo-fencing)
- **Offline Sync**: Sync data when connection restored

### 9.6 Analytics and Reporting (Priority: Medium)
- **Dashboard Widgets**: Customizable dashboard with key metrics
- **Predictive Analytics**: Predict overtime needs, leave trends
- **Performance Reports**: Employee productivity metrics
- **Compliance Reports**: Export for regulatory requirements
- **Custom Reports**: User-defined report builder
- **Visualizations**: Charts and graphs for trends

### 9.7 Performance Optimization (Priority: Medium)
- **Pagination**: All list endpoints should support pagination
- **Caching**: Redis cache for frequently accessed data (schedules, roles)
- **Query Optimization**: Add indexes, optimize N+1 queries
- **Batch Operations**: Bulk employee import, bulk schedule generation
- **Lazy Loading**: Frontend lazy load large lists
- **GraphQL**: Optional GraphQL API for flexible queries

### 9.8 Integration and Extensions (Priority: Low)
- **LDAP/AD Integration**: Connect to corporate Active Directory
- **Payroll System Integration**: Export wage data to accounting software
- **Email Integration**: Send emails for approvals/reminders
- **SMS Gateway**: Send SMS alerts for critical events
- **Slack Integration**: Post notifications to Slack channels
- **API Webhook Hooks**: Allow external systems to listen to events

### 9.9 Department and Organization (Priority: Low)
- **Multi-Department View**: Admins see cross-department analytics
- **Department Hierarchy**: Parent and child departments
- **Cost Centers**: Assign employees to cost centers for billing
- **Company Policies**: Configure policies per department (leave days, overtime rules)
- **Organization Chart**: Visual org chart with reporting relationships

### 9.10 Data Management (Priority: Low)
- **Data Export/Import**: Excel bulk import/export
- **Backup Strategy**: Automated backup to cloud storage
- **Data Retention**: Configurable data retention policies
- **Archive Old Data**: Archive completed cycles to separate storage
- **GDPR Compliance**: Right to be forgotten, data portability
- **Data Encryption**: Encrypt sensitive fields at rest

---

## 10. How to Run the Project

### 10.1 Prerequisites
- **Operating System**: WSL (Windows Subsystem for Linux), Linux, or macOS
- **Docker & Docker Compose**: For database container
- **Python 3.11**: For backend development
- **Node.js 18+**: For frontend development
- **Git**: For version control
- **Terminal**: Bash or compatible shell

### 10.2 Backend Setup

#### Step 1: Install Python Dependencies
```bash
cd /home/tw10576/major-v11/backend

# Create virtual environment (optional but recommended)
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### Step 2: Start PostgreSQL Database
```bash
cd /home/tw10576/major-v11

# Start database container
docker-compose up -d postgres

# Wait for database to be ready
docker-compose logs -f postgres
# Watch for: "database system is ready to accept connections"
# Press Ctrl+C when ready
```

#### Step 3: Initialize Database
```bash
cd backend

# Create tables and seed demo data
python init_db.py
```

Expected output:
```
🔄 Connecting to database...
📋 Creating all tables...
✅ All tables created!
👤 Initializing admin user...
✅ Database initialized!

📊 Created:
   ✓ All database tables
   ✓ 1 Admin user
   ✓ Demo departments
   ✓ Demo managers
   ✓ Demo employees
   ✓ Demo roles
   ✓ Demo shifts
   ✓ Demo schedules

🚀 Ready for testing!
```

#### Step 4: Start Backend Server
```bash
cd backend

# Run the application
python run.py
```

Backend starts on `http://localhost:8000` with:
- ✅ FastAPI application
- ✅ APScheduler background tasks (leave reminders, payroll)
- ✅ Swagger API docs at http://localhost:8000/docs

### 10.3 Frontend Setup

#### Step 1: Install Dependencies
```bash
cd /home/tw10576/major-v11/frontend

# Install npm packages
npm install
```

#### Step 2: Start Development Server
```bash
# In another terminal
cd /home/tw10576/major-v11/frontend

# Start Vite dev server
npm run dev
```

Frontend available at `http://localhost:5173` (Vite dev server)

Or access through backend proxy:
`http://localhost:8000` (if frontend built and served from backend)

### 10.4 Environment Variables

#### Backend Configuration (`backend/app/config.py`)
```python
# Database
DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/shift_scheduler"

# Security (change in production!)
SECRET_KEY = "your-secret-key-change-in-production-please"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# CORS Origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dev server
]
```

### 10.5 Login Credentials

After initialization, use these test accounts:

**Admin:**
- Username: `admin`
- Password: `admin123`

**Manager (Assembly Department):**
- Username: `manager1`
- Password: `manager123`

**Manager (Production Department):**
- Username: `manager2`
- Password: `manager123`

**Employees:**
- Username: `john.smith`, `sarah.j`, `michael.c`
- Password: `employee123` (for all)

### 10.6 Running Tests

**Leave Reminder Tests:**
```bash
cd backend
python test_leave_reminders.py
```

**Night Work Detection Tests:**
```bash
cd backend
python test_night_work.py
```

**Integration Tests:**
```bash
cd backend
python test_integration_complete.py
```

**Wage Calculation Tests:**
```bash
cd backend
python test_wage_calculation.py
```

All tests should pass with ✅ status.

### 10.7 Common Troubleshooting

#### Database Connection Fails
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# If not running, start it
docker-compose up -d postgres

# Check database logs
docker-compose logs postgres
```

#### "Address already in use" (Port 8000)
```bash
# Another process using port 8000
# Either kill it or change port in run.py

# List processes using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

#### "Address already in use" (Port 5173 Frontend)
```bash
# Another Vite instance running
# Kill or use different port

npm run dev -- --port 5174
```

#### Module Not Found / Import Errors
```bash
# Ensure you're in correct directory and venv activated
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

#### Database Tables Not Created
```bash
# Run initialization again
cd backend
python init_db.py

# Or reset database entirely
docker-compose down -v  # Removes volume
docker-compose up -d postgres
python init_db.py
```

#### Frontend Can't Reach Backend API
```bash
# Check backend is running
curl http://localhost:8000/

# Check CORS is configured for frontend origin
# In backend/app/config.py, ensure frontend URL is in CORS_ORIGINS

# Clear browser cache and localStorage
# DevTools → Application → Clear Storage
```

### 10.8 Building for Production

#### Backend Build (Docker)
```bash
cd backend

# Build Docker image
docker build -t shift-scheduler-backend:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=<strong-key> \
  shift-scheduler-backend:latest
```

#### Frontend Build
```bash
cd frontend

# Build for production
npm run build

# Output in dist/ folder
# Deploy to CDN or web server

# Or build Docker image for frontend
docker build -t shift-scheduler-frontend:latest .
```

#### Docker Compose for Production
```bash
# Update docker-compose.yml to include backend and frontend services
docker-compose -f docker-compose.prod.yml up -d
```

---

## 11. Architecture Decision Records

### 11.1 Database: PostgreSQL + SQLAlchemy Async
- **Decision**: Use PostgreSQL with SQLAlchemy async ORM
- **Rationale**: 
  - Relational schema provides data integrity
  - Async support matches FastAPI's async nature
  - Wide adoption means easy hiring and maintenance
  - Strong ACID guarantees for financial data (wages)

### 11.2 Schedule Generation: OR-Tools CP-SAT
- **Decision**: Use Google OR-Tools constraint solver
- **Rationale**:
  - Handles complex scheduling constraints efficiently
  - Provides optimal solutions vs greedy algorithms
  - Open-source and battle-tested in logistics
  - Supports realistic factory constraints

### 11.3 Authentication: JWT Tokens
- **Decision**: Stateless JWT tokens instead of sessions
- **Rationale**:
  - Scales horizontally (no session storage needed)
  - Works well with mobile and SPA frontends
  - Industry standard for API authentication
  - Simpler deployment (no session server required)

### 11.4 Scheduled Jobs: APScheduler
- **Decision**: Use APScheduler for background jobs
- **Rationale**:
  - In-process scheduling (simple deployment)
  - Works with async code
  - No external dependencies (Celery, Redis)
  - Good for single-instance deployments

### 11.5 Frontend: React + Vite
- **Decision**: React SPA with Vite build tool
- **Rationale**:
  - React has large ecosystem and talent pool
  - Vite provides fast development experience
  - Simple deployment (static files)
  - Good performance with TreeShaking and code splitting

---

## Conclusion

This Factory Shift Scheduling and Attendance Management System provides a comprehensive solution for factory operations with:
- ✅ Complete shift scheduling with optimization
- ✅ Real-time attendance tracking with night work detection
- ✅ Leave management with balance enforcement
- ✅ Overtime tracking and management
- ✅ Wage calculation for part-time employees
- ✅ Role-based access control for security
- ✅ Background scheduled tasks for automation
- ✅ Multiple export formats for reporting

The architecture is designed to be maintainable, scalable, and suitable for deployment in factory environments. While some limitations exist (see Section 8), the system provides a solid foundation for factory operations with clear paths for future enhancements.

For questions or contributions, refer to existing code documentation in individual files and the comprehensive test suites demonstrating feature usage.
■Summary:
Overall, high evaluations were received. The shift scheduler feature was particularly well-received.
 
■Detailed Feedback and Requests:
 
Comprehensive Management of Attendance Data:
It is necessary to centrally manage comprehensive data related to employees, including attendance status, various types of leave (including paid leave, half-day leave, and compensatory leave), overtime hours, working hours, and approval status.
 
Proxy Login:
For cases where the subject is unable to take leave or log attendance,
 
Paid Leave Reminder Function:
Automatically manage the remaining days of paid leave and send reminders to encourage employees to take leave, while also allowing managers to monitor leave trends.
 
Distinction Between Overtime and Late-Night Work Hours:
Automatically detect late-night work hours and calculate various allowances based on actual overtime hours and late-night work hours.
 
Data Output for Part-Time Employee Wage Calculation:
Automate wage calculations for part-time employees on a fixed cycle (15-day closing, 18-day wage confirmation).
 
Clocking in/out via Facial Recognition or ID Card Touch:
Record accurate, secure, and reliable attendance data using facial recognition or ID card touch clocking.
 
(That Concludes)
Features can be implemented 
Comprehensive Management of Attendance Data: It is necessary to centrally manage comprehensive data related to employees, including attendance status, various types of leave (including paid leave, half-day leave, and compensatory leave), overtime hours, working hours, and approval status. 
Paid Leave Reminder Function: Automatically manage the remaining days of paid leave and send reminders to encourage employees to take leave, while also allowing managers to monitor leave trends. 
Distinction Between Overtime and Late-Night Work Hours: Automatically detect late-night work hours and calculate various allowances based on actual overtime hours and late-night work hours. Automate wage calculations for part-time employees on a fixed cycle (15-day closing, 18-day wage confirmation).
Data Output for Part-Time Employee Wage Calculation:
Automate wage calculations for part-time employees on a fixed cycle (15-day closing, 18-day wage confirmation).
30 day logic
