"""
Paid Leave Reminder Management Service
Manages leave balances, reminders, and trends
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Employee, LeaveRequest, LeaveBalance, LeaveReminder, 
    LeaveStatus, User, Notification
)


class LeaveReminderService:
    """Service for managing paid leave reminders and balance tracking"""

    @staticmethod
    async def check_leave_balance(
        db: AsyncSession,
        employee_id: int,
        year: int = None
    ) -> Dict:
        """
        Check current leave balance for an employee
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            year: Year to check (default: current year)
            
        Returns:
            Dictionary with leave balance information
        """
        if year is None:
            year = date.today().year
        
        # Get employee
        emp_result = await db.execute(select(Employee).where(Employee.id == employee_id))
        employee = emp_result.scalar_one_or_none()
        
        if not employee:
            return {}
        
        # Get leave balance record
        balance_result = await db.execute(
            select(LeaveBalance).where(
                and_(
                    LeaveBalance.employee_id == employee_id,
                    LeaveBalance.year == year
                )
            )
        )
        leave_balance = balance_result.scalar_one_or_none()
        
        # Get all approved leaves for the year
        leave_result = await db.execute(
            select(LeaveRequest).where(
                and_(
                    LeaveRequest.employee_id == employee_id,
                    LeaveRequest.status == LeaveStatus.APPROVED,
                    LeaveRequest.start_date >= date(year, 1, 1),
                    LeaveRequest.end_date <= date(year, 12, 31)
                )
            )
        )
        approved_leaves = leave_result.scalars().all()
        
        # Calculate used and remaining
        paid_used = sum(
            (leave.end_date - leave.start_date).days + 1
            for leave in approved_leaves
            if leave.leave_type == 'paid'
        )
        unpaid_used = sum(
            (leave.end_date - leave.start_date).days + 1
            for leave in approved_leaves
            if leave.leave_type == 'unpaid'
        )
        
        total_entitlement = employee.paid_leave_per_year
        remaining = max(0, total_entitlement - paid_used)
        usage_percentage = (paid_used / total_entitlement * 100) if total_entitlement > 0 else 0
        
        # Update or create balance record
        if not leave_balance:
            leave_balance = LeaveBalance(
                employee_id=employee_id,
                year=year,
                total_paid_leave=total_entitlement,
                used_paid_leave=paid_used,
                remaining_paid_leave=remaining,
                total_unpaid_leave=unpaid_used
            )
            db.add(leave_balance)
            await db.commit()
        else:
            leave_balance.total_paid_leave = total_entitlement
            leave_balance.used_paid_leave = paid_used
            leave_balance.remaining_paid_leave = remaining
            leave_balance.total_unpaid_leave = unpaid_used
            leave_balance.last_updated = datetime.utcnow()
            db.add(leave_balance)
            await db.commit()
        
        return {
            'employee_id': employee_id,
            'year': year,
            'total_entitlement': total_entitlement,
            'paid_used': paid_used,
            'unpaid_used': unpaid_used,
            'remaining': remaining,
            'usage_percentage': round(usage_percentage, 2),
            'balance_record_id': leave_balance.id
        }

    @staticmethod
    async def send_reminders_to_low_balance(
        db: AsyncSession,
        threshold_days: int = 3
    ) -> List[Dict]:
        """
        Send reminders to employees with low remaining paid leave
        
        Args:
            db: AsyncSession
            threshold_days: Reminder threshold (default: 3 days)
            
        Returns:
            List of reminders sent
        """
        year = date.today().year
        reminders_sent = []
        
        # Get all active employees
        emp_result = await db.execute(
            select(Employee).where(Employee.is_active == True)
        )
        employees = emp_result.scalars().all()
        
        for employee in employees:
            # Check leave balance
            balance_info = await LeaveReminderService.check_leave_balance(db, employee.id, year)
            
            if balance_info.get('remaining', 0) <= threshold_days and balance_info.get('remaining', 0) > 0:
                # Check if reminder already sent today
                today = date.today()
                existing_reminder = (await db.execute(
                    select(LeaveReminder).where(
                        and_(
                            LeaveReminder.employee_id == employee.id,
                            func.date(LeaveReminder.reminder_date) == today,
                            LeaveReminder.reminder_type == 'low_balance'
                        )
                    )
                )).scalar_one_or_none()
                
                if not existing_reminder:
                    # Create reminder
                    reminder = LeaveReminder(
                        employee_id=employee.id,
                        reminder_date=datetime.utcnow(),
                        remaining_days_at_time=balance_info.get('remaining', 0),
                        reminder_type='low_balance'
                    )
                    db.add(reminder)
                    
                    # Create notification for employee user if exists
                    if employee.user_id:
                        notification = Notification(
                            user_id=employee.user_id,
                            title='Paid Leave Reminder',
                            message=f'You have {balance_info.get("remaining", 0):.1f} days of paid leave remaining for {year}. '
                                   f'Remember to plan your leave accordingly.',
                            notification_type='leave_reminder',
                            related_id=reminder.id
                        )
                        db.add(notification)
                    
                    reminders_sent.append({
                        'employee_id': employee.id,
                        'employee_name': f'{employee.first_name} {employee.last_name}',
                        'remaining_days': balance_info.get('remaining', 0),
                        'reminder_type': 'low_balance',
                        'sent_at': reminder.reminder_date.isoformat()
                    })
        
        await db.commit()
        return reminders_sent

    @staticmethod
    async def send_mid_year_reminder(
        db: AsyncSession
    ) -> List[Dict]:
        """
        Send mid-year reminders (around June/July) to employees
        
        Args:
            db: AsyncSession
            
        Returns:
            List of reminders sent
        """
        year = date.today().year
        reminders_sent = []
        
        # Get all active employees
        emp_result = await db.execute(
            select(Employee).where(Employee.is_active == True)
        )
        employees = emp_result.scalars().all()
        
        for employee in employees:
            # Check leave balance
            balance_info = await LeaveReminderService.check_leave_balance(db, employee.id, year)
            
            # Check if mid-year reminder already sent
            existing_reminder = (await db.execute(
                select(LeaveReminder).where(
                    and_(
                        LeaveReminder.employee_id == employee.id,
                        LeaveReminder.reminder_type == 'mid_year'
                    )
                )
            )).scalar_one_or_none()
            
            if not existing_reminder:
                reminder = LeaveReminder(
                    employee_id=employee.id,
                    reminder_date=datetime.utcnow(),
                    remaining_days_at_time=balance_info.get('remaining', 0),
                    reminder_type='mid_year'
                )
                db.add(reminder)
                
                # Create notification
                if employee.user_id:
                    notification = Notification(
                        user_id=employee.user_id,
                        title='Mid-Year Leave Reminder',
                        message=f'You have used {balance_info.get("paid_used", 0)} out of {balance_info.get("total_entitlement", 0)} '
                               f'paid leave days. Consider planning your remaining {balance_info.get("remaining", 0)} days.',
                        notification_type='leave_reminder',
                        related_id=reminder.id
                    )
                    db.add(notification)
                
                reminders_sent.append({
                    'employee_id': employee.id,
                    'employee_name': f'{employee.first_name} {employee.last_name}',
                    'remaining_days': balance_info.get('remaining', 0),
                    'used_days': balance_info.get('paid_used', 0),
                    'reminder_type': 'mid_year',
                    'sent_at': reminder.reminder_date.isoformat()
                })
        
        await db.commit()
        return reminders_sent

    @staticmethod
    async def send_year_end_reminder(
        db: AsyncSession,
        days_before_year_end: int = 30
    ) -> List[Dict]:
        """
        Send year-end reminder to encourage leave usage before year ends
        
        Args:
            db: AsyncSession
            days_before_year_end: Days before year end to send reminder
            
        Returns:
            List of reminders sent
        """
        year = date.today().year
        reminders_sent = []
        
        # Get all active employees
        emp_result = await db.execute(
            select(Employee).where(Employee.is_active == True)
        )
        employees = emp_result.scalars().all()
        
        for employee in employees:
            balance_info = await LeaveReminderService.check_leave_balance(db, employee.id, year)
            
            # Only send if there are unused days
            if balance_info.get('remaining', 0) > 0:
                # Check if year-end reminder already sent
                existing_reminder = (await db.execute(
                    select(LeaveReminder).where(
                        and_(
                            LeaveReminder.employee_id == employee.id,
                            LeaveReminder.reminder_type == 'year_end'
                        )
                    )
                )).scalar_one_or_none()
                
                if not existing_reminder:
                    reminder = LeaveReminder(
                        employee_id=employee.id,
                        reminder_date=datetime.utcnow(),
                        remaining_days_at_time=balance_info.get('remaining', 0),
                        reminder_type='year_end'
                    )
                    db.add(reminder)
                    
                    # Create notification
                    if employee.user_id:
                        notification = Notification(
                            user_id=employee.user_id,
                            title='Year-End Leave Reminder',
                            message=f'You still have {balance_info.get("remaining", 0)} days of paid leave remaining for {year}. '
                                   f'Please plan to use these days before the year ends to avoid forfeiture.',
                            notification_type='leave_reminder',
                            related_id=reminder.id
                        )
                        db.add(notification)
                    
                    reminders_sent.append({
                        'employee_id': employee.id,
                        'employee_name': f'{employee.first_name} {employee.last_name}',
                        'remaining_days': balance_info.get('remaining', 0),
                        'reminder_type': 'year_end',
                        'sent_at': reminder.reminder_date.isoformat()
                    })
        
        await db.commit()
        return reminders_sent

    @staticmethod
    async def track_reminder_sent(
        db: AsyncSession,
        reminder_id: int,
        action_taken: str = None,
        is_acknowledged: bool = False
    ) -> Optional[LeaveReminder]:
        """
        Track reminder acknowledgement and actions taken
        
        Args:
            db: AsyncSession
            reminder_id: Reminder ID
            action_taken: Action taken by employee
            is_acknowledged: Whether reminder was acknowledged
            
        Returns:
            Updated LeaveReminder object or None
        """
        reminder_result = await db.execute(
            select(LeaveReminder).where(LeaveReminder.id == reminder_id)
        )
        reminder = reminder_result.scalar_one_or_none()
        
        if reminder:
            if is_acknowledged:
                reminder.is_acknowledged = True
                reminder.acknowledgment_date = datetime.utcnow()
            
            if action_taken:
                reminder.action_taken = action_taken
            
            reminder.updated_at = datetime.utcnow()
            db.add(reminder)
            await db.commit()
            await db.refresh(reminder)
        
        return reminder

    @staticmethod
    async def get_leave_trends(
        db: AsyncSession,
        employee_id: int,
        num_years: int = 3
    ) -> Dict:
        """
        Analyze leave trends for an employee over multiple years
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            num_years: Number of years to analyze
            
        Returns:
            Dictionary with trend analysis
        """
        current_year = date.today().year
        trends = []
        
        for year_offset in range(num_years):
            year = current_year - year_offset
            
            # Get leave balance for the year
            balance_result = await db.execute(
                select(LeaveBalance).where(
                    and_(
                        LeaveBalance.employee_id == employee_id,
                        LeaveBalance.year == year
                    )
                )
            )
            balance = balance_result.scalar_one_or_none()
            
            if balance:
                trends.append({
                    'year': year,
                    'total_entitlement': balance.total_paid_leave,
                    'used': balance.used_paid_leave,
                    'remaining': balance.remaining_paid_leave,
                    'usage_percentage': round((balance.used_paid_leave / balance.total_paid_leave * 100) if balance.total_paid_leave > 0 else 0, 2)
                })
        
        # Calculate average usage
        avg_usage = sum(t['usage_percentage'] for t in trends) / len(trends) if trends else 0
        
        return {
            'employee_id': employee_id,
            'analysis_period': f'Last {num_years} years',
            'trends': trends,
            'average_usage_percentage': round(avg_usage, 2),
            'trend_direction': 'increasing' if trends and trends[-1]['usage_percentage'] > avg_usage else 'decreasing'
        }

    @staticmethod
    async def get_department_leave_summary(
        db: AsyncSession,
        department_id: int,
        year: int = None
    ) -> Dict:
        """
        Get leave summary for all employees in a department
        
        Args:
            db: AsyncSession
            department_id: Department ID
            year: Year to check (default: current year)
            
        Returns:
            Dictionary with department leave statistics
        """
        if year is None:
            year = date.today().year
        
        # Get all employees in department
        emp_result = await db.execute(
            select(Employee).where(
                and_(
                    Employee.department_id == department_id,
                    Employee.is_active == True
                )
            )
        )
        employees = emp_result.scalars().all()
        
        employee_summaries = []
        total_balance = 0
        total_used = 0
        total_remaining = 0
        
        for employee in employees:
            balance_info = await LeaveReminderService.check_leave_balance(db, employee.id, year)
            
            employee_summaries.append({
                'employee_id': employee.employee_id,
                'employee_name': f'{employee.first_name} {employee.last_name}',
                'entitlement': balance_info.get('total_entitlement', 0),
                'used': balance_info.get('paid_used', 0),
                'remaining': balance_info.get('remaining', 0),
                'usage_percentage': balance_info.get('usage_percentage', 0)
            })
            
            total_balance += balance_info.get('total_entitlement', 0)
            total_used += balance_info.get('paid_used', 0)
            total_remaining += balance_info.get('remaining', 0)
        
        avg_usage = (total_used / total_balance * 100) if total_balance > 0 else 0
        
        return {
            'department_id': department_id,
            'year': year,
            'total_employees': len(employees),
            'total_entitlement': total_balance,
            'total_used': total_used,
            'total_remaining': total_remaining,
            'average_usage_percentage': round(avg_usage, 2),
            'employee_summaries': employee_summaries
        }
