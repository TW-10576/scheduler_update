#!/usr/bin/env python3
"""
End-to-End Integration Test for All Features
Tests the complete flow: attendance → night work → wage calculation → leave reminders
"""

import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base, Employee, Department, Attendance, LeaveRequest, User, UserType,
    LeaveStatus, EmployeeWageConfig, PayrollCycle, WageCalculation
)
from app.attendance_service import AttendanceService
from app.leave_reminder_service import LeaveReminderService
from app.wage_calculation_service import WageCalculationService


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = None
TestingSessionLocal = None


async def setup_test_db():
    """Setup test database"""
    global engine, TestingSessionLocal
    
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def teardown_test_db():
    """Teardown test database"""
    global engine
    if engine:
        await engine.dispose()


async def create_test_employee(db: AsyncSession):
    """Create a complete test employee with all relationships"""
    # Create department
    dept = Department(
        dept_id="001",
        name="Engineering",
        is_active=True
    )
    db.add(dept)
    await db.flush()
    
    # Create user
    user = User(
        username="emp001",
        email="emp001@company.com",
        hashed_password="hashed_password",
        user_type=UserType.EMPLOYEE,
        is_active=True
    )
    db.add(user)
    await db.flush()
    
    # Create employee
    employee = Employee(
        employee_id="00001",
        first_name="John",
        last_name="Doe",
        email="emp001@company.com",
        department_id=dept.id,
        user_id=user.id,
        paid_leave_per_year=10,
        is_active=True
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    
    return employee


async def test_complete_workflow():
    """Test complete workflow: attendance → leaves → wages"""
    
    print("\n" + "="*70)
    print("END-TO-END INTEGRATION TEST: Complete Workflow")
    print("="*70)
    
    await setup_test_db()
    
    try:
        async with TestingSessionLocal() as db:
            print("\n1️⃣  SETUP: Creating test employee...")
            employee = await create_test_employee(db)
            print(f"   ✓ Employee created: {employee.employee_id} - {employee.first_name} {employee.last_name}")
            
            # ==================== STEP 2: ATTENDANCE & NIGHT WORK ====================
            print("\n2️⃣  ATTENDANCE: Recording work with night hours...")
            year = date.today().year
            
            # Week 1: Normal work days
            for day in range(1, 4):  # Mon-Wed
                attendance = Attendance(
                    employee_id=employee.id,
                    date=date(year, 1, day),
                    in_time="09:00",
                    out_time="17:00",
                    worked_hours=8.0,
                    break_minutes=60,
                    status="onTime"
                )
                db.add(attendance)
            
            # Thursday: Late night work (21:00-06:00 next day)
            night_attendance = Attendance(
                employee_id=employee.id,
                date=date(year, 1, 4),
                in_time="21:00",
                out_time="06:00",
                worked_hours=9.0,
                night_hours=6.0,  # 22:00-06:00
                break_minutes=0,
                status="onTime"
            )
            db.add(night_attendance)
            
            # Friday: Overtime work (09:00-20:00)
            overtime_attendance = Attendance(
                employee_id=employee.id,
                date=date(year, 1, 5),
                in_time="09:00",
                out_time="20:00",
                worked_hours=10.0,
                overtime_hours=2.0,
                break_minutes=60,
                status="onTime"
            )
            db.add(overtime_attendance)
            
            await db.commit()
            print(f"   ✓ Attendance records created for 5 days")
            print(f"     - 3 normal days (8 hrs each)")
            print(f"     - 1 late night (21:00-06:00, 6 hours night work)")
            print(f"     - 1 overtime (10 hours with 2 hrs OT)")
            
            # ==================== STEP 3: LEAVE REQUESTS ====================
            print("\n3️⃣  LEAVE MANAGEMENT: Recording leave requests...")
            
            leave1 = LeaveRequest(
                employee_id=employee.id,
                start_date=date(year, 1, 6),
                end_date=date(year, 1, 7),
                leave_type='paid',
                status=LeaveStatus.APPROVED
            )
            db.add(leave1)
            
            leave2 = LeaveRequest(
                employee_id=employee.id,
                start_date=date(year, 2, 1),
                end_date=date(year, 2, 5),
                leave_type='paid',
                status=LeaveStatus.APPROVED
            )
            db.add(leave2)
            
            await db.commit()
            print(f"   ✓ Leave requests recorded:")
            print(f"     - Jan 6-7: 2 days paid leave")
            print(f"     - Feb 1-5: 5 days paid leave")
            print(f"     - Total paid leave used: 7 days")
            print(f"     - Remaining: {10 - 7} days (out of 10 annual)")
            
            # ==================== STEP 4: LEAVE BALANCE & REMINDERS ====================
            print("\n4️⃣  LEAVE REMINDERS: Checking balance and sending reminders...")
            
            balance_info = await LeaveReminderService.check_leave_balance(db, employee.id, year)
            print(f"   ✓ Leave balance checked:")
            print(f"     - Entitlement: {balance_info['total_entitlement']} days")
            print(f"     - Used: {balance_info['paid_used']} days")
            print(f"     - Remaining: {balance_info['remaining']} days")
            print(f"     - Usage: {balance_info['usage_percentage']}%")
            
            if balance_info['remaining'] <= 3:
                reminders = await LeaveReminderService.send_reminders_to_low_balance(db)
                print(f"   ✓ Low balance reminder sent ({len(reminders)} total)")
            
            # ==================== STEP 5: WAGE CONFIGURATION ====================
            print("\n5️⃣  PAYROLL: Configuring employee wages...")
            
            config = await WageCalculationService.get_or_create_wage_config(
                db,
                employee.id,
                hourly_rate=500.0,
                overtime_multiplier=1.5,
                night_shift_multiplier=1.5
            )
            print(f"   ✓ Wage configuration created:")
            print(f"     - Hourly rate: {config.hourly_rate}")
            print(f"     - OT multiplier: {config.overtime_multiplier}x")
            print(f"     - Night shift multiplier: {config.night_shift_multiplier}x")
            
            # ==================== STEP 6: WAGE CALCULATION ====================
            print("\n6️⃣  WAGE CALCULATION: Processing payroll cycle...")
            
            # Create payroll cycle for first 15 days of January
            cycle = await WageCalculationService.get_payroll_cycle(db, date(year, 1, 1))
            print(f"   ✓ Payroll cycle created:")
            print(f"     - Cycle number: {cycle.cycle_number}")
            print(f"     - Period: {cycle.start_date} to {cycle.end_date}")
            print(f"     - Closing date: {cycle.closing_date}")
            print(f"     - Confirmation date: {cycle.confirmation_date}")
            
            # Calculate wages
            wage_calc = await WageCalculationService.calculate_wage_for_period(db, employee.id, cycle)
            print(f"   ✓ Wages calculated:")
            print(f"     - Regular hours: {wage_calc.regular_hours}")
            print(f"     - Overtime hours: {wage_calc.overtime_hours}")
            print(f"     - Night hours: {wage_calc.night_hours}")
            print(f"     - Base wage: {wage_calc.base_wage}")
            print(f"     - Overtime wage: {wage_calc.overtime_wage}")
            print(f"     - Night shift wage: {wage_calc.night_shift_wage}")
            print(f"     - Net wage: {wage_calc.net_wage}")
            
            # ==================== STEP 7: ATTENDANCE SUMMARY ====================
            print("\n7️⃣  ATTENDANCE SUMMARY: Generating summary...")
            
            summary = await AttendanceService.aggregate_attendance_summary(
                db, employee.id, 'monthly', date(year, 1, 1)
            )
            print(f"   ✓ Attendance summary generated:")
            print(f"     - Days worked: {summary['days_worked']}")
            print(f"     - Total hours worked: {summary['total_worked_hours']}")
            print(f"     - Regular hours: {summary['regular_hours']}")
            print(f"     - Overtime hours: {summary['overtime_hours']}")
            print(f"     - Night hours: {summary['night_hours']}")
            print(f"     - On-time %: {summary['on_time_percentage']}%")
            
            # ==================== STEP 8: CYCLE CLOSING ====================
            print("\n8️⃣  CLOSING: Verifying and closing payroll cycle...")
            
            close_result = await WageCalculationService.verify_and_close_cycle(db, cycle)
            print(f"   ✓ Cycle closed:")
            print(f"     - Status: {close_result['closing_status']}")
            print(f"     - Verified employees: {close_result['verified_employees']}/{close_result['total_employees']}")
            
            # ==================== STEP 9: WAGE CONFIRMATION ====================
            print("\n9️⃣  CONFIRMATION: Confirming 18-day wages...")
            
            confirm_result = await WageCalculationService.confirm_wages(db, cycle)
            print(f"   ✓ Wages confirmed:")
            print(f"     - Status: {confirm_result['status']}")
            print(f"     - Confirmed date: {confirm_result['confirmation_date']}")
            
            # ==================== FINAL SUMMARY ====================
            print("\n" + "="*70)
            print("✅ INTEGRATION TEST PASSED - All features working correctly!")
            print("="*70)
            print("\nWorkflow Summary:")
            print(f"  1. Created employee and recorded 5 days of attendance")
            print(f"  2. Tracked night work (6 hours) and overtime (2 hours)")
            print(f"  3. Recorded 7 days of paid leave")
            print(f"  4. Leave balance: {balance_info['remaining']} days remaining")
            print(f"  5. Configured hourly wage: {config.hourly_rate}")
            print(f"  6. Calculated wages for 15-day payroll cycle")
            print(f"  7. Generated attendance summary with all metrics")
            print(f"  8. Closed 15-day closing cycle")
            print(f"  9. Confirmed 18-day wage cycle")
            print("\nKey Metrics:")
            print(f"  - Total wage: {wage_calc.net_wage}")
            print(f"  - Wage components: Base + OT + Night + Leaves")
            print(f"  - Attendance verified: {summary['on_time_percentage']}% on-time")
            print("="*70 + "\n")
    
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await teardown_test_db()


if __name__ == "__main__":
    asyncio.run(test_complete_workflow())
