"""
Comprehensive Attendance Data Management Service
Handles aggregation, calculation, and validation of attendance data
"""

from datetime import datetime, time, timedelta, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Attendance, CheckInOut, LeaveRequest, Schedule, Employee,
    AttendanceSummary, LeaveStatus, OvertimeWorked, LateNightWork
)


class AttendanceService:
    """Service for comprehensive attendance data management"""

    @staticmethod
    async def calculate_worked_hours(
        in_time_str: str,
        out_time_str: str,
        break_minutes: int = 0
    ) -> float:
        """
        Calculate total worked hours from check-in and check-out times
        
        Args:
            in_time_str: Check-in time as "HH:MM"
            out_time_str: Check-out time as "HH:MM"
            break_minutes: Break time in minutes
            
        Returns:
            Total worked hours as float
        """
        try:
            in_time = datetime.strptime(in_time_str, '%H:%M').time()
            out_time = datetime.strptime(out_time_str, '%H:%M').time()
            
            # Handle case where out_time is on next day (e.g., 22:00 to 06:00)
            if out_time <= in_time:
                in_dt = datetime.combine(date.today(), in_time)
                out_dt = datetime.combine(date.today() + timedelta(days=1), out_time)
            else:
                in_dt = datetime.combine(date.today(), in_time)
                out_dt = datetime.combine(date.today(), out_time)
            
            total_minutes = (out_dt - in_dt).total_seconds() / 60
            worked_minutes = max(0, total_minutes - break_minutes)
            worked_hours = worked_minutes / 60
            
            return round(worked_hours, 2)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    async def calculate_overtime_vs_night(
        in_time_str: str,
        out_time_str: str,
        scheduled_hours: float = 8.0,
        break_minutes: int = 0
    ) -> Tuple[float, float]:
        """
        Distinguish between overtime (hours > 8 per day) and night work hours (22:00+)
        
        Args:
            in_time_str: Check-in time as "HH:MM"
            out_time_str: Check-out time as "HH:MM"
            scheduled_hours: Scheduled hours for the day (default 8.0)
            break_minutes: Break time in minutes
            
        Returns:
            Tuple of (regular_hours, overtime_hours, night_hours)
        """
        try:
            in_time = datetime.strptime(in_time_str, '%H:%M').time()
            out_time = datetime.strptime(out_time_str, '%H:%M').time()
            
            # Worked hours
            total_worked = await AttendanceService.calculate_worked_hours(
                in_time_str, out_time_str, break_minutes
            )
            
            # Overtime calculation (simple: total - scheduled)
            overtime_hours = max(0, total_worked - scheduled_hours)
            regular_hours = min(total_worked, scheduled_hours)
            
            # Night work calculation (22:00 to 06:00)
            night_hours = await AttendanceService.calculate_night_work_hours(
                in_time_str, out_time_str
            )
            
            return round(regular_hours, 2), round(overtime_hours, 2), round(night_hours, 2)
        except (ValueError, TypeError):
            return 0.0, 0.0, 0.0

    @staticmethod
    async def calculate_night_work_hours(
        in_time_str: str,
        out_time_str: str
    ) -> float:
        """
        Calculate hours worked during late-night period (22:00 to 06:00)
        
        Args:
            in_time_str: Check-in time as "HH:MM"
            out_time_str: Check-out time as "HH:MM"
            
        Returns:
            Hours worked during night period
        """
        try:
            in_time = datetime.strptime(in_time_str, '%H:%M').time()
            out_time = datetime.strptime(out_time_str, '%H:%M').time()
            
            night_start = datetime.strptime('22:00', '%H:%M').time()
            night_end = datetime.strptime('06:00', '%H:%M').time()
            
            # Create datetime objects
            if out_time <= in_time:
                # Spans midnight
                in_dt = datetime.combine(date.today(), in_time)
                out_dt = datetime.combine(date.today() + timedelta(days=1), out_time)
            else:
                in_dt = datetime.combine(date.today(), in_time)
                out_dt = datetime.combine(date.today(), out_time)
            
            night_start_dt = datetime.combine(date.today(), night_start)
            night_end_dt = datetime.combine(date.today() + timedelta(days=1), night_end)
            
            # Calculate overlap with night period
            overlap_start = max(in_dt, night_start_dt)
            overlap_end = min(out_dt, night_end_dt)
            
            if overlap_end > overlap_start:
                night_minutes = (overlap_end - overlap_start).total_seconds() / 60
                return round(night_minutes / 60, 2)
            
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    async def aggregate_attendance_summary(
        db: AsyncSession,
        employee_id: int,
        period_type: str = 'monthly',
        period_date: date = None
    ) -> Dict:
        """
        Aggregate comprehensive attendance summary for an employee over a period
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            period_type: 'daily', 'weekly', 'monthly', 'yearly'
            period_date: Start date of the period
            
        Returns:
            Dictionary with aggregated attendance data
        """
        if period_date is None:
            period_date = date.today()
        
        # Determine period range
        if period_type == 'daily':
            start_date = period_date
            end_date = period_date
        elif period_type == 'weekly':
            start_date = period_date - timedelta(days=period_date.weekday())
            end_date = start_date + timedelta(days=6)
        elif period_type == 'monthly':
            start_date = period_date.replace(day=1)
            if period_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1) - timedelta(days=1)
        elif period_type == 'yearly':
            start_date = period_date.replace(month=1, day=1)
            end_date = period_date.replace(month=12, day=31)
        else:
            start_date = period_date
            end_date = period_date
        
        # Fetch attendance records
        attendance_result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.employee_id == employee_id,
                    Attendance.date >= start_date,
                    Attendance.date <= end_date
                )
            ).options(selectinload(Attendance.schedule))
        )
        attendance_records = attendance_result.scalars().all()
        
        # Fetch leave requests
        leave_result = await db.execute(
            select(LeaveRequest).where(
                and_(
                    LeaveRequest.employee_id == employee_id,
                    LeaveRequest.start_date <= end_date,
                    LeaveRequest.end_date >= start_date,
                    LeaveRequest.status == LeaveStatus.APPROVED
                )
            )
        )
        leave_records = leave_result.scalars().all()
        
        # Fetch night work records
        night_result = await db.execute(
            select(LateNightWork).where(
                and_(
                    LateNightWork.employee_id == employee_id,
                    LateNightWork.work_date >= start_date,
                    LateNightWork.work_date <= end_date
                )
            )
        )
        night_records = night_result.scalars().all()
        
        # Calculate statistics
        total_days_in_period = (end_date - start_date).days + 1
        
        # Hours aggregation
        total_worked_hours = sum(r.worked_hours or 0 for r in attendance_records)
        overtime_hours = sum(r.overtime_hours or 0 for r in attendance_records)
        night_hours = sum(r.night_hours or 0 for r in attendance_records)
        break_hours = sum(r.break_minutes or 0 for r in attendance_records) / 60
        
        # Days worked
        days_worked = len([r for r in attendance_records if r.worked_hours and r.worked_hours > 0])
        
        # Attendance status
        on_time_count = len([r for r in attendance_records if r.status == 'onTime'])
        slightly_late_count = len([r for r in attendance_records if r.status == 'slightlyLate'])
        late_count = len([r for r in attendance_records if r.status == 'late'])
        very_late_count = len([r for r in attendance_records if r.status == 'veryLate'])
        total_attended = on_time_count + slightly_late_count + late_count + very_late_count
        
        on_time_percentage = (on_time_count / total_attended * 100) if total_attended > 0 else 0
        
        # Leave aggregation
        paid_leave_days = 0
        unpaid_leave_days = 0
        half_day_leave = 0
        
        for leave in leave_records:
            days = (leave.end_date - leave.start_date).days + 1
            if leave.leave_type == 'paid':
                paid_leave_days += days
            elif leave.leave_type == 'unpaid':
                unpaid_leave_days += days
            elif leave.leave_type == 'half-day':
                half_day_leave += days * 0.5
        
        total_leave_days = paid_leave_days + unpaid_leave_days + half_day_leave
        
        return {
            'employee_id': employee_id,
            'period_type': period_type,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'total_days_in_period': total_days_in_period,
            'days_worked': days_worked,
            'days_absent': total_days_in_period - days_worked - int(total_leave_days),
            'total_worked_hours': round(total_worked_hours, 2),
            'regular_hours': round(total_worked_hours - overtime_hours - night_hours, 2),
            'overtime_hours': round(overtime_hours, 2),
            'night_hours': round(night_hours, 2),
            'break_hours': round(break_hours, 2),
            'paid_leave_days': paid_leave_days,
            'unpaid_leave_days': unpaid_leave_days,
            'half_day_leave': half_day_leave,
            'total_leave_days': total_leave_days,
            'on_time_count': on_time_count,
            'slightly_late_count': slightly_late_count,
            'late_count': late_count,
            'very_late_count': very_late_count,
            'on_time_percentage': round(on_time_percentage, 2),
            'attendance_records_count': len(attendance_records),
            'night_work_records': len(night_records)
        }

    @staticmethod
    async def validate_attendance_data(
        db: AsyncSession,
        employee_id: int,
        date_range_start: date,
        date_range_end: date
    ) -> Dict:
        """
        Validate attendance data for completeness and accuracy
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            date_range_start: Start date of range to validate
            date_range_end: End date of range to validate
            
        Returns:
            Dictionary with validation results
        """
        # Fetch attendance records
        attendance_result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.employee_id == employee_id,
                    Attendance.date >= date_range_start,
                    Attendance.date <= date_range_end
                )
            )
        )
        attendance_records = attendance_result.scalars().all()
        
        issues = []
        warnings = []
        
        for record in attendance_records:
            # Check for missing check-in/check-out
            if not record.in_time:
                issues.append(f"Missing check-in time on {record.date}")
            if not record.out_time:
                issues.append(f"Missing check-out time on {record.date}")
            
            # Check for missing worked hours
            if record.in_time and record.out_time and record.worked_hours == 0:
                warnings.append(f"Zero worked hours on {record.date} despite check-in/out")
            
            # Check for excessive hours (> 16)
            if record.worked_hours > 16:
                warnings.append(f"Excessive hours ({record.worked_hours}) on {record.date}")
            
            # Check for missing status
            if not record.status:
                warnings.append(f"Missing attendance status on {record.date}")
        
        total_records = len(attendance_records)
        records_with_issues = len([r for r in attendance_records if not r.in_time or not r.out_time])
        
        return {
            'employee_id': employee_id,
            'validation_date': datetime.now().isoformat(),
            'period_start': date_range_start.isoformat(),
            'period_end': date_range_end.isoformat(),
            'total_records': total_records,
            'records_with_issues': records_with_issues,
            'validation_percentage': round((total_records - records_with_issues) / total_records * 100, 2) if total_records > 0 else 0,
            'issues': issues,
            'warnings': warnings,
            'is_valid': len(issues) == 0 and records_with_issues == 0
        }

    @staticmethod
    async def create_or_update_attendance_summary(
        db: AsyncSession,
        employee_id: int,
        period_type: str = 'monthly',
        period_date: date = None
    ) -> Optional[AttendanceSummary]:
        """
        Create or update attendance summary record
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            period_type: 'daily', 'weekly', 'monthly', 'yearly'
            period_date: Start date of the period
            
        Returns:
            AttendanceSummary object or None
        """
        if period_date is None:
            period_date = date.today()
        
        # Get aggregated data
        summary_data = await AttendanceService.aggregate_attendance_summary(
            db, employee_id, period_type, period_date
        )
        
        # Determine period end date
        if period_type == 'daily':
            period_end_date = period_date
        elif period_type == 'weekly':
            period_end_date = period_date + timedelta(days=6)
        elif period_type == 'monthly':
            if period_date.month == 12:
                period_end_date = period_date.replace(year=period_date.year + 1, month=1) - timedelta(days=1)
            else:
                period_end_date = period_date.replace(month=period_date.month + 1) - timedelta(days=1)
        elif period_type == 'yearly':
            period_end_date = period_date.replace(month=12, day=31)
        else:
            period_end_date = period_date
        
        # Check if summary already exists
        existing_result = await db.execute(
            select(AttendanceSummary).where(
                and_(
                    AttendanceSummary.employee_id == employee_id,
                    AttendanceSummary.period_type == period_type,
                    AttendanceSummary.period_date == period_date
                )
            )
        )
        existing_summary = existing_result.scalar_one_or_none()
        
        if existing_summary:
            # Update existing
            existing_summary.total_days_in_period = summary_data['total_days_in_period']
            existing_summary.days_worked = summary_data['days_worked']
            existing_summary.days_absent = summary_data['days_absent']
            existing_summary.total_worked_hours = summary_data['total_worked_hours']
            existing_summary.regular_hours = summary_data['regular_hours']
            existing_summary.overtime_hours = summary_data['overtime_hours']
            existing_summary.night_hours = summary_data['night_hours']
            existing_summary.break_hours = summary_data['break_hours']
            existing_summary.paid_leave_days = summary_data['paid_leave_days']
            existing_summary.unpaid_leave_days = summary_data['unpaid_leave_days']
            existing_summary.half_day_leave = summary_data['half_day_leave']
            existing_summary.total_leave_days = summary_data['total_leave_days']
            existing_summary.on_time_count = summary_data['on_time_count']
            existing_summary.slightly_late_count = summary_data['slightly_late_count']
            existing_summary.late_count = summary_data['late_count']
            existing_summary.very_late_count = summary_data['very_late_count']
            existing_summary.on_time_percentage = summary_data['on_time_percentage']
            existing_summary.summary_data = summary_data
            existing_summary.updated_at = datetime.utcnow()
            db.add(existing_summary)
        else:
            # Create new
            existing_summary = AttendanceSummary(
                employee_id=employee_id,
                period_type=period_type,
                period_date=period_date,
                period_end_date=period_end_date,
                total_days_in_period=summary_data['total_days_in_period'],
                days_worked=summary_data['days_worked'],
                days_absent=summary_data['days_absent'],
                total_worked_hours=summary_data['total_worked_hours'],
                regular_hours=summary_data['regular_hours'],
                overtime_hours=summary_data['overtime_hours'],
                night_hours=summary_data['night_hours'],
                break_hours=summary_data['break_hours'],
                paid_leave_days=summary_data['paid_leave_days'],
                unpaid_leave_days=summary_data['unpaid_leave_days'],
                half_day_leave=summary_data['half_day_leave'],
                total_leave_days=summary_data['total_leave_days'],
                on_time_count=summary_data['on_time_count'],
                slightly_late_count=summary_data['slightly_late_count'],
                late_count=summary_data['late_count'],
                very_late_count=summary_data['very_late_count'],
                on_time_percentage=summary_data['on_time_percentage'],
                summary_data=summary_data
            )
            db.add(existing_summary)
        
        await db.commit()
        await db.refresh(existing_summary)
        return existing_summary
