"""
Helper utilities for attendance and leave management
"""

from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import LeaveRequest, LeaveStatus, LeaveBalance, Notification

async def calculate_leave_days(start_date: date, end_date: date, leave_type: str) -> float:
    """
    Calculate number of leave days between two dates
    
    Args:
        start_date: Start date of leave
        end_date: End date of leave
        leave_type: Type of leave ('paid_leave', 'half_day_leave', 'compensatory_leave')
        
    Returns:
        Number of days (including half days as 0.5)
    """
    if start_date > end_date:
        return 0
    
    # Count business days (excluding weekends if needed)
    days_diff = (end_date - start_date).days + 1  # +1 to include start_date
    
    # For half_day_leave, count as 0.5
    if leave_type == 'half_day_leave':
        return 0.5
    
    # For other types, count full days
    return float(days_diff)


async def get_leave_balance(db: AsyncSession, employee_id: int, year: int = None) -> LeaveBalance:
    """
    Get or create leave balance record for an employee
    
    Args:
        db: AsyncSession
        employee_id: Employee ID
        year: Year (default: current year)
        
    Returns:
        LeaveBalance object
    """
    if year is None:
        year = date.today().year
    
    result = await db.execute(
        select(LeaveBalance).where(
            and_(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == year
            )
        )
    )
    balance = result.scalar_one_or_none()
    
    if not balance:
        # Create new balance record for this year
        balance = LeaveBalance(
            employee_id=employee_id,
            year=year,
            total_paid_leave=10,  # Default to 10 days (should come from employee config)
            used_paid_leave=0,
            remaining_paid_leave=10,
            total_unpaid_leave=0
        )
        db.add(balance)
        await db.flush()
    
    return balance


async def deduct_leave_balance(
    db: AsyncSession,
    employee_id: int,
    days_to_deduct: float,
    leave_type: str
) -> tuple[bool, str]:
    """
    Deduct leave days from employee's balance
    
    Args:
        db: AsyncSession
        employee_id: Employee ID
        days_to_deduct: Number of days to deduct
        leave_type: Type of leave
        
    Returns:
        (success: bool, message: str)
    """
    # Only deduct paid leave from balance
    if leave_type != 'paid_leave':
        return (True, "Non-paid leave does not affect paid leave balance")
    
    balance = await get_leave_balance(db, employee_id)
    
    # Check if enough balance
    if balance.remaining_paid_leave < days_to_deduct:
        return (False, f"Insufficient balance. Remaining: {balance.remaining_paid_leave}, Requested: {days_to_deduct}")
    
    # Deduct
    balance.used_paid_leave = round(balance.used_paid_leave + days_to_deduct, 2)
    balance.remaining_paid_leave = round(balance.total_paid_leave - balance.used_paid_leave, 2)
    balance.last_updated = datetime.utcnow()
    
    return (True, f"Deducted {days_to_deduct} days. Remaining: {balance.remaining_paid_leave}")


async def create_notification(
    db: AsyncSession,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "general",
    related_id: int = None
) -> Notification:
    """
    Create a notification for a user
    
    Args:
        db: AsyncSession
        user_id: User ID to receive notification
        title: Notification title
        message: Notification message body
        notification_type: Type of notification (leave_approved, overtime_approved, balance_low, etc.)
        related_id: ID of related record (leave_request_id, overtime_request_id, etc.)
        
    Returns:
        Notification object
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        related_id=related_id,
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notification)
    await db.flush()
    return notification


async def check_and_send_low_balance_notification(
    db: AsyncSession,
    employee_id: int,
    threshold: float = 3.0
) -> bool:
    """
    Check if employee has low leave balance and send notification
    
    Args:
        db: AsyncSession
        employee_id: Employee ID
        threshold: Number of days below which to send notification (default: 3)
        
    Returns:
        True if notification was sent, False otherwise
    """
    balance = await get_leave_balance(db, employee_id)
    
    if balance.remaining_paid_leave <= threshold and balance.remaining_paid_leave > 0:
        # Get employee to find associated user
        from app.models import Employee
        result = await db.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()
        
        if employee and employee.user_id:
            await create_notification(
                db,
                employee.user_id,
                "Low Leave Balance",
                f"You have only {balance.remaining_paid_leave} days of paid leave remaining. Please plan accordingly.",
                notification_type="leave_balance_low",
                related_id=employee_id
            )
            return True
    
    return False


async def is_employee_on_approved_leave(
    db: AsyncSession,
    employee_id: int,
    check_date: date
) -> bool:
    """
    Check if employee has approved leave on the given date
    
    Args:
        db: AsyncSession
        employee_id: Employee ID
        check_date: Date to check
        
    Returns:
        True if employee is on approved leave, False otherwise
    """
    result = await db.execute(
        select(LeaveRequest).where(
            and_(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.status == LeaveStatus.APPROVED,
                LeaveRequest.start_date <= check_date,
                LeaveRequest.end_date >= check_date
            )
        )
    )
    leave_request = result.scalar_one_or_none()
    return leave_request is not None
