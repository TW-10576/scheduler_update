"""
Database Models for Shift Scheduler - Normalized Schema V6
Optimized with clean foreign key relationships
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, JSON, Date, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class UserType(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class LeaveStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    """User model for authentication (Admin, Manager, Employee logins)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    user_type = Column(SQLEnum(UserType), nullable=False)  # admin, manager, employee
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sent_messages = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender", cascade="all, delete-orphan")
    received_messages = relationship("Message", foreign_keys="Message.recipient_id", back_populates="recipient", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")


class Department(Base):
    """Department model - Master table for all departments"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    dept_id = Column(String(3), unique=True, nullable=False, index=True)  # 3-digit auto-generated dept ID (001, 002, etc.)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships - all operational tables reference this
    managers = relationship("Manager", back_populates="department", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="department", cascade="all, delete-orphan")
    roles = relationship("Role", back_populates="department", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="department", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="department", cascade="all, delete-orphan")


class Manager(Base):
    """Manager model - Links user to department"""
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', name='fk_manager_user'), nullable=False, unique=True, index=True)
    department_id = Column(Integer, ForeignKey('departments.id', name='fk_manager_department'), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    department = relationship("Department", back_populates="managers")
    leave_requests = relationship("LeaveRequest", back_populates="manager")


class Employee(Base):
    """Employee model"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(10), unique=True, nullable=False, index=True)  # 5-digit employee ID like "00001"
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    address = Column(Text)
    department_id = Column(Integer, ForeignKey('departments.id', name='fk_emp_department'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', name='fk_emp_role'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id', name='fk_emp_user'), nullable=True)
    weekly_hours = Column(Float, default=40)
    daily_max_hours = Column(Float, default=8)
    shifts_per_week = Column(Integer, default=5)
    paid_leave_per_year = Column(Integer, default=10)  # Paid leave days per year
    skills = Column(JSON, default=list)
    hire_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="employees")
    role = relationship("Role", back_populates="employees")
    user = relationship("User", foreign_keys=[user_id])
    schedules = relationship("Schedule", back_populates="employee", cascade="all, delete-orphan")
    leave_requests = relationship("LeaveRequest", back_populates="employee", cascade="all, delete-orphan")
    check_ins = relationship("CheckInOut", back_populates="employee", cascade="all, delete-orphan")
    overtime_tracking = relationship("OvertimeTracking", back_populates="employee", cascade="all, delete-orphan")
    overtime_requests = relationship("OvertimeRequest", back_populates="employee", cascade="all, delete-orphan")
    overtime_worked = relationship("OvertimeWorked", back_populates="employee", cascade="all, delete-orphan")
    # New relationships for wage and leave management
    wage_config = relationship("EmployeeWageConfig", back_populates="employee", uselist=False, cascade="all, delete-orphan")
    wage_calculations = relationship("WageCalculation", back_populates="employee", cascade="all, delete-orphan")
    leave_balance = relationship("LeaveBalance", back_populates="employee", cascade="all, delete-orphan")
    leave_reminders = relationship("LeaveReminder", back_populates="employee", cascade="all, delete-orphan")
    night_work = relationship("LateNightWork", back_populates="employee", cascade="all, delete-orphan")
    attendance_summaries = relationship("AttendanceSummary", back_populates="employee", cascade="all, delete-orphan")


class Role(Base):
    """Role/Position Type model"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    department_id = Column(Integer, ForeignKey('departments.id', name='fk_role_department'), nullable=False)
    priority = Column(Integer, default=50)
    priority_percentage = Column(Integer, default=50)
    required_skills = Column(JSON, default=list)
    break_minutes = Column(Integer, default=60)
    weekend_required = Column(Boolean, default=False)
    schedule_config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="roles")
    employees = relationship("Employee", back_populates="role")
    schedules = relationship("Schedule", back_populates="role", cascade="all, delete-orphan")
    shifts = relationship("Shift", back_populates="role", cascade="all, delete-orphan")


class Schedule(Base):
    """Schedule/Shift Assignment model"""
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey('departments.id', name='fk_schedule_department'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_schedule_employee'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', name='fk_schedule_role'), nullable=False)
    shift_id = Column(Integer, ForeignKey('shifts.id', name='fk_schedule_shift'), nullable=True)  # Optional - can be custom if None
    date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5))
    end_time = Column(String(5))
    status = Column(String(20), default='scheduled')  # scheduled, completed, missed, cancelled
    notes = Column(Text)
    day_priority = Column(Integer, default=1)  # For priority-based distribution
    is_overtime = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    department = relationship("Department", back_populates="schedules")
    employee = relationship("Employee", back_populates="schedules")
    role = relationship("Role", back_populates="schedules")
    shift = relationship("Shift")  # Reference to assigned shift (if any)
    check_in = relationship("CheckInOut", back_populates="schedule", uselist=False, cascade="all, delete-orphan")
    attendance = relationship("Attendance", back_populates="schedule", uselist=False, cascade="all, delete-orphan")


class LeaveRequest(Base):
    """Leave requests with approval workflow"""
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_leave_employee'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    leave_type = Column(String(20), nullable=False)
    reason = Column(Text)
    status = Column(SQLEnum(LeaveStatus), default=LeaveStatus.PENDING)
    manager_id = Column(Integer, ForeignKey('managers.id', name='fk_leave_manager'))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    employee = relationship("Employee", back_populates="leave_requests")
    manager = relationship("Manager", back_populates="leave_requests")


class CheckInOut(Base):
    """Employee Check-In/Out tracking"""
    __tablename__ = "check_ins"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_checkin_employee'), nullable=False)
    schedule_id = Column(Integer, ForeignKey('schedules.id', name='fk_checkin_schedule'), nullable=True)
    date = Column(Date, nullable=False, index=True)
    check_in_time = Column(DateTime)
    check_out_time = Column(DateTime)
    check_in_status = Column(String(20))  # onTime, slightlyLate, late, veryLate
    check_out_status = Column(String(20))
    location = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee", back_populates="check_ins")
    schedule = relationship("Schedule", back_populates="check_in")


class Attendance(Base):
    """Attendance records with worked hours tracking"""
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_attendance_employee'), nullable=False)
    schedule_id = Column(Integer, ForeignKey('schedules.id', name='fk_attendance_schedule'), nullable=True)
    date = Column(Date, nullable=False, index=True)
    in_time = Column(String(5))  # HH:MM format
    out_time = Column(String(5))  # HH:MM format
    status = Column(String(20))  # onTime, slightlyLate, late, veryLate, missed
    out_status = Column(String(20))
    worked_hours = Column(Float, default=0)
    overtime_hours = Column(Float, default=0)
    night_hours = Column(Float, default=0)  # Hours worked between 22:00 and 06:00
    night_allowance = Column(Float, default=0)  # Calculated night shift allowance
    break_minutes = Column(Integer, default=0)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee")
    schedule = relationship("Schedule", back_populates="attendance")


class Message(Base):
    """Messaging system"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id', name='fk_message_sender'), nullable=False)
    recipient_id = Column(Integer, ForeignKey('users.id', name='fk_message_recipient'), nullable=True)
    department_id = Column(Integer, ForeignKey('departments.id', name='fk_message_department'), nullable=True)
    subject = Column(String(200))
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    is_deleted_by_sender = Column(Boolean, default=False)
    is_deleted_by_recipient = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_at = Column(DateTime)

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="received_messages")
    department = relationship("Department", back_populates="messages")


class Notification(Base):
    """System notifications"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', name='fk_notification_user'), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50))
    related_id = Column(Integer)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")


class Unavailability(Base):
    """Employee unavailability/constraints"""
    __tablename__ = "unavailability"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_unavail_employee'), nullable=False)
    date = Column(Date, nullable=False, index=True)
    reason = Column(String(100), nullable=True)  # sick, personal, training, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    employee = relationship("Employee")


class Shift(Base):
    """Shift/Shift Type model - for detailed shift timing and configuration"""
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey('roles.id', name='fk_shift_role'), nullable=False)
    name = Column(String(100), nullable=False)
    start_time = Column(String(5), nullable=False)  # HH:MM format
    end_time = Column(String(5), nullable=False)  # HH:MM format
    priority = Column(Integer, default=50)
    min_emp = Column(Integer, default=1)  # Minimum employees required
    max_emp = Column(Integer, default=10)  # Maximum employees allowed
    schedule_config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    role = relationship("Role", back_populates="shifts")


class OvertimeStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OvertimeTracking(Base):
    """Track monthly overtime for each employee"""
    __tablename__ = "overtime_tracking"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_overtime_employee'), nullable=False)
    month = Column(Integer, nullable=False)  # Month (1-12)
    year = Column(Integer, nullable=False)  # Year
    allocated_hours = Column(Float, default=0)  # Hours allocated/approved for this month
    used_hours = Column(Float, default=0)  # Hours already used
    remaining_hours = Column(Float, default=0)  # Remaining available hours
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = relationship("Employee", back_populates="overtime_tracking")


class OvertimeRequest(Base):
    """Employee overtime requests"""
    __tablename__ = "overtime_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_ot_request_employee'), nullable=False)
    request_date = Column(Date, nullable=False)  # Date of overtime request
    from_time = Column(String(5), nullable=True)  # Start time (HH:MM format)
    to_time = Column(String(5), nullable=True)  # End time (HH:MM format)
    request_hours = Column(Float, nullable=False)  # Hours requested
    reason = Column(Text, nullable=False)  # Reason for overtime
    status = Column(SQLEnum(OvertimeStatus), default=OvertimeStatus.PENDING)
    manager_id = Column(Integer, ForeignKey('users.id', name='fk_ot_request_manager'), nullable=True)
    manager_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = relationship("Employee", back_populates="overtime_requests")
    manager = relationship("User")


class OvertimeWorked(Base):
    """Track actual overtime worked per day"""
    __tablename__ = "overtime_worked"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_ot_worked_employee'), nullable=False)
    work_date = Column(Date, nullable=False, index=True)
    overtime_hours = Column(Float, nullable=False)  # Hours worked over 8 hrs/day
    approval_status = Column(SQLEnum(OvertimeStatus), default=OvertimeStatus.PENDING)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = relationship("Employee", back_populates="overtime_worked")


class LateNightWork(Base):
    """Track late-night work hours (22:00 onwards) separately from overtime"""
    __tablename__ = "late_night_work"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_night_employee'), nullable=False)
    work_date = Column(Date, nullable=False, index=True)
    night_start_time = Column(String(5), nullable=False)  # HH:MM format (usually 22:00 or later)
    night_end_time = Column(String(5), nullable=True)  # HH:MM format
    night_hours = Column(Float, nullable=False)  # Hours worked between 22:00 and next day 06:00
    night_allowance_rate = Column(Float, default=1.5)  # 1.5x or 2x multiplier
    night_allowance_amount = Column(Float, default=0)  # Calculated allowance (hourly_rate * hours * multiplier)
    approval_status = Column(SQLEnum(OvertimeStatus), default=OvertimeStatus.PENDING)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = relationship("Employee")


class LeaveBalance(Base):
    """Track cumulative leave balance for employees"""
    __tablename__ = "leave_balance"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_leave_balance_employee'), nullable=False)
    year = Column(Integer, nullable=False)  # Year of the balance
    total_paid_leave = Column(Float, default=0)  # Total entitled paid leave for the year
    used_paid_leave = Column(Float, default=0)  # Used paid leave
    remaining_paid_leave = Column(Float, default=0)  # Remaining paid leave
    total_unpaid_leave = Column(Float, default=0)  # Total unpaid leave taken
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    employee = relationship("Employee")


class LeaveReminder(Base):
    """Track paid leave reminders sent to employees"""
    __tablename__ = "leave_reminders"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_reminder_employee'), nullable=False)
    reminder_date = Column(DateTime, nullable=False)  # When the reminder was sent
    remaining_days_at_time = Column(Float, nullable=False)  # Remaining paid leave days at time of reminder
    reminder_type = Column(String(50), default='low_balance')  # low_balance, mid_year, year_end
    is_acknowledged = Column(Boolean, default=False)
    acknowledgment_date = Column(DateTime, nullable=True)
    action_taken = Column(Text, nullable=True)  # What action employee took (e.g., "Requested 2 days leave")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    employee = relationship("Employee")


class EmployeeWageConfig(Base):
    """Employee wage configuration for part-time wage calculations"""
    __tablename__ = "employee_wage_config"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_wage_config_employee'), nullable=False, unique=True)
    hourly_rate = Column(Float, nullable=False, default=0)  # Base hourly rate
    regular_shift_premium = Column(Float, default=1.0)  # Multiplier for regular shifts (1.0 = no premium)
    overtime_multiplier = Column(Float, default=1.5)  # Overtime payment multiplier (1.5x, 2x, etc.)
    night_shift_multiplier = Column(Float, default=1.5)  # Night shift allowance multiplier (22:00+)
    holiday_multiplier = Column(Float, default=2.0)  # Holiday work multiplier
    is_part_time = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = relationship("Employee")


class PayrollCycle(Base):
    """Track payroll cycles: 15-day closing and 18-day wage confirmation"""
    __tablename__ = "payroll_cycles"

    id = Column(Integer, primary_key=True, index=True)
    cycle_number = Column(Integer, nullable=False)  # 1-24 for 15-day cycles in a year
    year = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)  # First day of 15-day period
    end_date = Column(Date, nullable=False)  # Last day of 15-day period
    closing_date = Column(Date, nullable=True)  # 15-day closing date (data verification deadline)
    confirmation_date = Column(Date, nullable=True)  # 18-day wage confirmation date (wage payment confirmation)
    is_closed = Column(Boolean, default=False)
    is_confirmed = Column(Boolean, default=False)
    total_employees = Column(Integer, default=0)
    processed_employees = Column(Integer, default=0)
    confirmed_employees = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WageCalculation(Base):
    """Store calculated wages for each payroll cycle"""
    __tablename__ = "wage_calculations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_wage_calc_employee'), nullable=False)
    payroll_cycle_id = Column(Integer, ForeignKey('payroll_cycles.id', name='fk_wage_calc_cycle'), nullable=False)
    
    # Hours breakdown
    regular_hours = Column(Float, default=0)  # Regular work hours
    overtime_hours = Column(Float, default=0)  # Overtime hours (8+ hours/day)
    night_hours = Column(Float, default=0)  # Late-night work hours (22:00+)
    break_hours = Column(Float, default=0)  # Break/unpaid hours
    total_worked_hours = Column(Float, default=0)  # Total hours worked
    
    # Days breakdown
    working_days = Column(Integer, default=0)  # Days actually worked
    leave_days = Column(Float, default=0)  # Leave days taken
    paid_leave_days = Column(Float, default=0)  # Paid leave days
    unpaid_leave_days = Column(Float, default=0)  # Unpaid leave days
    
    # Wage calculations
    base_wage = Column(Float, default=0)  # Regular hours * hourly rate
    overtime_wage = Column(Float, default=0)  # Overtime hours * hourly rate * multiplier
    night_shift_wage = Column(Float, default=0)  # Night hours * hourly rate * multiplier
    holiday_wage = Column(Float, default=0)  # Holiday work wage
    
    # Allowances and deductions
    shift_premium = Column(Float, default=0)  # Any shift-specific bonuses
    meal_allowance = Column(Float, default=0)
    transportation_allowance = Column(Float, default=0)
    other_allowance = Column(Float, default=0)
    
    total_allowance = Column(Float, default=0)  # Sum of all allowances
    total_deduction = Column(Float, default=0)  # Sum of all deductions
    net_wage = Column(Float, default=0)  # Total wage to be paid
    
    # Status tracking
    calculation_date = Column(DateTime, default=datetime.utcnow)
    closing_verified = Column(Boolean, default=False)  # Verified during 15-day closing
    wage_confirmed = Column(Boolean, default=False)  # Confirmed during 18-day confirmation
    is_paid = Column(Boolean, default=False)
    payment_date = Column(DateTime, nullable=True)
    
    # Notes and references
    notes = Column(Text, nullable=True)
    calculation_details = Column(JSON, default=dict)  # Detailed calculation breakdown
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = relationship("Employee")
    payroll_cycle = relationship("PayrollCycle")


class AttendanceSummary(Base):
    """Centralized comprehensive attendance data for employees"""
    __tablename__ = "attendance_summary"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('employees.id', name='fk_att_summary_employee'), nullable=False)
    
    # Period identification
    period_type = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly'
    period_date = Column(Date, nullable=False)  # Start date of period
    period_end_date = Column(Date, nullable=True)  # End date of period (for weekly/monthly/yearly)
    
    # Comprehensive attendance data
    total_days_in_period = Column(Integer, default=0)  # Calendar days in period
    working_days = Column(Integer, default=0)  # Days employee was scheduled
    days_worked = Column(Integer, default=0)  # Days actually worked
    days_absent = Column(Integer, default=0)  # Days absent without leave
    
    # Hours breakdown
    total_scheduled_hours = Column(Float, default=0)  # Total hours scheduled
    total_worked_hours = Column(Float, default=0)  # Total hours actually worked
    regular_hours = Column(Float, default=0)  # Regular 8-hour shift hours
    overtime_hours = Column(Float, default=0)  # Overtime hours (8+ per day)
    night_hours = Column(Float, default=0)  # Late-night work hours
    break_hours = Column(Float, default=0)  # Break time
    
    # Leave breakdown
    paid_leave_days = Column(Float, default=0)
    half_day_leave = Column(Float, default=0)  # Half-day leaves (counted as 0.5)
    compensatory_leave = Column(Float, default=0)  # Comp leave used
    unpaid_leave_days = Column(Float, default=0)
    total_leave_days = Column(Float, default=0)
    
    # Attendance status
    on_time_count = Column(Integer, default=0)
    slightly_late_count = Column(Integer, default=0)
    late_count = Column(Integer, default=0)
    very_late_count = Column(Integer, default=0)
    on_time_percentage = Column(Float, default=0)
    
    # Approval and verification
    approval_status = Column(String(20), default='pending')  # pending, approved, rejected
    verified_by_manager = Column(Boolean, default=False)
    manager_verification_date = Column(DateTime, nullable=True)
    approved_by_admin = Column(Boolean, default=False)
    admin_approval_date = Column(DateTime, nullable=True)
    
    # Notes and metadata
    notes = Column(Text, nullable=True)
    summary_data = Column(JSON, default=dict)  # Additional summary data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    employee = relationship("Employee")
