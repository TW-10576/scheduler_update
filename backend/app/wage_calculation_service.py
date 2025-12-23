"""
Part-Time Employee Wage Calculation Service
Handles 15-day closing and 18-day wage confirmation cycles
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import calendar

from app.models import (
    Employee, Attendance, OvertimeWorked, LateNightWork,
    EmployeeWageConfig, PayrollCycle, WageCalculation,
    LeaveRequest, LeaveStatus
)


class WageCalculationService:
    """Service for part-time employee wage calculations"""

    @staticmethod
    async def get_or_create_wage_config(
        db: AsyncSession,
        employee_id: int,
        hourly_rate: float = 0,
        overtime_multiplier: float = 1.5,
        night_shift_multiplier: float = 1.5
    ) -> EmployeeWageConfig:
        """
        Get or create wage configuration for employee
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            hourly_rate: Base hourly rate
            overtime_multiplier: Overtime payment multiplier
            night_shift_multiplier: Night shift payment multiplier
            
        Returns:
            EmployeeWageConfig object
        """
        # Check if config exists
        config_result = await db.execute(
            select(EmployeeWageConfig).where(
                EmployeeWageConfig.employee_id == employee_id
            )
        )
        config = config_result.scalar_one_or_none()
        
        if config:
            return config
        
        # Create new config
        config = EmployeeWageConfig(
            employee_id=employee_id,
            hourly_rate=hourly_rate,
            overtime_multiplier=overtime_multiplier,
            night_shift_multiplier=night_shift_multiplier,
            is_part_time=True,
            effective_from=date.today()
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def get_payroll_cycle(
        db: AsyncSession,
        start_date: date,
        end_date: date = None
    ) -> Optional[PayrollCycle]:
        """
        Get or create payroll cycle for given dates
        
        Args:
            db: AsyncSession
            start_date: Start date of 15-day period
            end_date: End date (calculated if not provided)
            
        Returns:
            PayrollCycle object or None
        """
        if end_date is None:
            end_date = start_date + timedelta(days=14)  # 15-day period
        
        # Check if cycle exists
        cycle_result = await db.execute(
            select(PayrollCycle).where(
                and_(
                    PayrollCycle.start_date == start_date,
                    PayrollCycle.end_date == end_date
                )
            )
        )
        cycle = cycle_result.scalar_one_or_none()
        
        if cycle:
            return cycle
        
        # Create new cycle
        year = start_date.year
        
        # Calculate cycle number (1-24 for 15-day cycles)
        days_from_year_start = (start_date - date(year, 1, 1)).days
        cycle_number = (days_from_year_start // 15) + 1
        
        cycle = PayrollCycle(
            cycle_number=cycle_number,
            year=year,
            start_date=start_date,
            end_date=end_date,
            closing_date=end_date + timedelta(days=1),  # Closing on next day (16th day for 15-day cycle)
            confirmation_date=end_date + timedelta(days=3)  # 18-day cycle confirmation
        )
        db.add(cycle)
        await db.commit()
        await db.refresh(cycle)
        return cycle

    @staticmethod
    async def calculate_wage_for_period(
        db: AsyncSession,
        employee_id: int,
        payroll_cycle: PayrollCycle
    ) -> WageCalculation:
        """
        Calculate wage for an employee for a payroll cycle
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            payroll_cycle: PayrollCycle object
            
        Returns:
            WageCalculation object
        """
        # Get employee and wage config
        emp_result = await db.execute(select(Employee).where(Employee.id == employee_id))
        employee = emp_result.scalar_one_or_none()
        
        config = await WageCalculationService.get_or_create_wage_config(db, employee_id)
        
        if config.hourly_rate <= 0:
            raise ValueError(f"Hourly rate not configured for employee {employee_id}")
        
        # Get attendance records for the period
        att_result = await db.execute(
            select(Attendance).where(
                and_(
                    Attendance.employee_id == employee_id,
                    Attendance.date >= payroll_cycle.start_date,
                    Attendance.date <= payroll_cycle.end_date
                )
            )
        )
        attendance_records = att_result.scalars().all()
        
        # Get leave records for the period
        leave_result = await db.execute(
            select(LeaveRequest).where(
                and_(
                    LeaveRequest.employee_id == employee_id,
                    LeaveRequest.status == LeaveStatus.APPROVED,
                    LeaveRequest.start_date <= payroll_cycle.end_date,
                    LeaveRequest.end_date >= payroll_cycle.start_date
                )
            )
        )
        leave_records = leave_result.scalars().all()
        
        # Calculate hours
        regular_hours = 0
        overtime_hours = 0
        night_hours = 0
        break_hours = 0
        
        for record in attendance_records:
            regular_hours += record.worked_hours - (record.overtime_hours or 0) - (record.night_hours or 0)
            overtime_hours += record.overtime_hours or 0
            night_hours += record.night_hours or 0
            break_hours += (record.break_minutes or 0) / 60
        
        # Calculate leave days
        paid_leave_days = 0
        unpaid_leave_days = 0
        
        for leave in leave_records:
            # Check if leave overlaps with payroll cycle
            overlap_start = max(leave.start_date, payroll_cycle.start_date)
            overlap_end = min(leave.end_date, payroll_cycle.end_date)
            
            if overlap_end >= overlap_start:
                days = (overlap_end - overlap_start).days + 1
                if leave.leave_type == 'paid':
                    paid_leave_days += days
                else:
                    unpaid_leave_days += days
        
        # Calculate wages
        base_wage = regular_hours * config.hourly_rate
        overtime_wage = overtime_hours * config.hourly_rate * config.overtime_multiplier
        night_shift_wage = night_hours * config.hourly_rate * config.night_shift_multiplier
        
        # Paid leave wage (assuming 8-hour days)
        paid_leave_wage = paid_leave_days * 8 * config.hourly_rate
        
        total_allowance = 0
        total_wage = base_wage + overtime_wage + night_shift_wage + paid_leave_wage
        
        # Create wage calculation record
        check_existing = (await db.execute(
            select(WageCalculation).where(
                and_(
                    WageCalculation.employee_id == employee_id,
                    WageCalculation.payroll_cycle_id == payroll_cycle.id
                )
            )
        )).scalar_one_or_none()
        
        if check_existing:
            wage_calc = check_existing
        else:
            wage_calc = WageCalculation(
                employee_id=employee_id,
                payroll_cycle_id=payroll_cycle.id
            )
        
        wage_calc.regular_hours = round(regular_hours, 2)
        wage_calc.overtime_hours = round(overtime_hours, 2)
        wage_calc.night_hours = round(night_hours, 2)
        wage_calc.break_hours = round(break_hours, 2)
        wage_calc.total_worked_hours = round(regular_hours + overtime_hours + night_hours, 2)
        
        wage_calc.working_days = len([r for r in attendance_records if r.worked_hours > 0])
        wage_calc.paid_leave_days = paid_leave_days
        wage_calc.unpaid_leave_days = unpaid_leave_days
        wage_calc.total_leave_days = paid_leave_days + unpaid_leave_days
        
        wage_calc.base_wage = round(base_wage, 2)
        wage_calc.overtime_wage = round(overtime_wage, 2)
        wage_calc.night_shift_wage = round(night_shift_wage, 2)
        wage_calc.shift_premium = round(paid_leave_wage, 2)
        
        wage_calc.total_allowance = round(total_allowance, 2)
        wage_calc.total_deduction = 0
        wage_calc.net_wage = round(total_wage, 2)
        
        wage_calc.calculation_details = {
            'regular_hours': round(regular_hours, 2),
            'overtime_hours': round(overtime_hours, 2),
            'night_hours': round(night_hours, 2),
            'break_hours': round(break_hours, 2),
            'base_wage': round(base_wage, 2),
            'overtime_wage': round(overtime_wage, 2),
            'night_shift_wage': round(night_shift_wage, 2),
            'paid_leave_wage': round(paid_leave_wage, 2),
            'wage_config': {
                'hourly_rate': config.hourly_rate,
                'overtime_multiplier': config.overtime_multiplier,
                'night_shift_multiplier': config.night_shift_multiplier
            }
        }
        
        db.add(wage_calc)
        await db.commit()
        await db.refresh(wage_calc)
        return wage_calc

    @staticmethod
    async def verify_and_close_cycle(
        db: AsyncSession,
        payroll_cycle: PayrollCycle
    ) -> Dict:
        """
        Verify and close 15-day payroll cycle
        
        Args:
            db: AsyncSession
            payroll_cycle: PayrollCycle object
            
        Returns:
            Dictionary with closing verification results
        """
        # Get all wage calculations for this cycle
        wage_result = await db.execute(
            select(WageCalculation).where(
                WageCalculation.payroll_cycle_id == payroll_cycle.id
            )
        )
        wage_calculations = wage_result.scalars().all()
        
        total_processed = 0
        verified_count = 0
        issues = []
        
        for wage_calc in wage_calculations:
            total_processed += 1
            
            # Basic validation
            if wage_calc.net_wage < 0:
                issues.append(f"Negative wage for employee {wage_calc.employee_id}")
            elif wage_calc.regular_hours + wage_calc.overtime_hours < 0:
                issues.append(f"Invalid hours for employee {wage_calc.employee_id}")
            else:
                verified_count += 1
                wage_calc.closing_verified = True
        
        # Update cycle
        payroll_cycle.is_closed = True
        payroll_cycle.processed_employees = total_processed
        payroll_cycle.confirmed_employees = verified_count
        payroll_cycle.updated_at = datetime.utcnow()
        
        db.add(payroll_cycle)
        await db.commit()
        
        return {
            'cycle_id': payroll_cycle.id,
            'cycle_number': payroll_cycle.cycle_number,
            'total_employees': total_processed,
            'verified_employees': verified_count,
            'issues': issues,
            'closing_status': 'success' if verified_count == total_processed else 'partial_with_issues'
        }

    @staticmethod
    async def confirm_wages(
        db: AsyncSession,
        payroll_cycle: PayrollCycle
    ) -> Dict:
        """
        Confirm 18-day wage cycle (3 days after 15-day closing)
        
        Args:
            db: AsyncSession
            payroll_cycle: PayrollCycle object
            
        Returns:
            Dictionary with confirmation results
        """
        if not payroll_cycle.is_closed:
            raise ValueError("Cycle must be closed before confirmation")
        
        # Get all wage calculations
        wage_result = await db.execute(
            select(WageCalculation).where(
                WageCalculation.payroll_cycle_id == payroll_cycle.id
            )
        )
        wage_calculations = wage_result.scalars().all()
        
        confirmed_count = 0
        for wage_calc in wage_calculations:
            wage_calc.wage_confirmed = True
            db.add(wage_calc)
            confirmed_count += 1
        
        # Update cycle
        payroll_cycle.is_confirmed = True
        payroll_cycle.confirmed_employees = confirmed_count
        payroll_cycle.updated_at = datetime.utcnow()
        
        db.add(payroll_cycle)
        await db.commit()
        
        return {
            'cycle_id': payroll_cycle.id,
            'cycle_number': payroll_cycle.cycle_number,
            'confirmed_employees': confirmed_count,
            'confirmation_date': payroll_cycle.confirmation_date.isoformat(),
            'status': 'confirmed'
        }

    @staticmethod
    async def get_wage_summary_for_employee(
        db: AsyncSession,
        employee_id: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Get wage summary for an employee over a date range
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with wage summary
        """
        # Get wage calculations for the period
        wage_result = await db.execute(
            select(WageCalculation).where(
                and_(
                    WageCalculation.employee_id == employee_id,
                    WageCalculation.calculation_date >= start_date,
                    WageCalculation.calculation_date <= end_date
                )
            ).options(selectinload(WageCalculation.payroll_cycle))
        )
        wage_calculations = wage_result.scalars().all()
        
        # Aggregate data
        total_regular_hours = sum(w.regular_hours for w in wage_calculations)
        total_overtime_hours = sum(w.overtime_hours for w in wage_calculations)
        total_night_hours = sum(w.night_hours for w in wage_calculations)
        total_worked_hours = sum(w.total_worked_hours for w in wage_calculations)
        
        total_base_wage = sum(w.base_wage for w in wage_calculations)
        total_overtime_wage = sum(w.overtime_wage for w in wage_calculations)
        total_night_wage = sum(w.night_shift_wage for w in wage_calculations)
        total_allowance = sum(w.total_allowance for w in wage_calculations)
        total_net_wage = sum(w.net_wage for w in wage_calculations)
        
        details = []
        for wage_calc in wage_calculations:
            details.append({
                'cycle_number': wage_calc.payroll_cycle.cycle_number,
                'cycle_start': wage_calc.payroll_cycle.start_date.isoformat(),
                'cycle_end': wage_calc.payroll_cycle.end_date.isoformat(),
                'regular_hours': wage_calc.regular_hours,
                'overtime_hours': wage_calc.overtime_hours,
                'night_hours': wage_calc.night_hours,
                'net_wage': wage_calc.net_wage,
                'status': 'confirmed' if wage_calc.wage_confirmed else ('verified' if wage_calc.closing_verified else 'pending')
            })
        
        return {
            'employee_id': employee_id,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'total_cycles': len(wage_calculations),
            'hours_breakdown': {
                'regular': round(total_regular_hours, 2),
                'overtime': round(total_overtime_hours, 2),
                'night_shift': round(total_night_hours, 2),
                'total': round(total_worked_hours, 2)
            },
            'wage_breakdown': {
                'base_wage': round(total_base_wage, 2),
                'overtime_wage': round(total_overtime_wage, 2),
                'night_shift_wage': round(total_night_wage, 2),
                'allowances': round(total_allowance, 2),
                'net_wage': round(total_net_wage, 2)
            },
            'cycle_details': details
        }

    @staticmethod
    async def apply_wage_config_changes(
        db: AsyncSession,
        employee_id: int,
        hourly_rate: float = None,
        overtime_multiplier: float = None,
        night_shift_multiplier: float = None,
        effective_date: date = None
    ) -> EmployeeWageConfig:
        """
        Apply changes to employee wage configuration
        
        Args:
            db: AsyncSession
            employee_id: Employee ID
            hourly_rate: New hourly rate
            overtime_multiplier: New overtime multiplier
            night_shift_multiplier: New night shift multiplier
            effective_date: Date when changes become effective
            
        Returns:
            Updated EmployeeWageConfig
        """
        if effective_date is None:
            effective_date = date.today()
        
        config = await WageCalculationService.get_or_create_wage_config(db, employee_id)
        
        if hourly_rate is not None:
            config.hourly_rate = hourly_rate
        if overtime_multiplier is not None:
            config.overtime_multiplier = overtime_multiplier
        if night_shift_multiplier is not None:
            config.night_shift_multiplier = night_shift_multiplier
        
        config.effective_from = effective_date
        config.updated_at = datetime.utcnow()
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        return config
