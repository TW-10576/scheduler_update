"""
Comprehensive Tests for Part-Time Wage Calculation
Tests wage calculations, payroll cycles, and related functionality
"""

import asyncio
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from decimal import Decimal

from app.models import Base, Employee, Department, EmployeeWageConfig, PayrollCycle, WageCalculation, Attendance
from app.wage_calculation_service import WageCalculationService
from app.database import get_db


# Test database setup
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


async def create_test_employee(db: AsyncSession, emp_id: int = 1):
    """Create a test employee"""
    # Create department first
    dept = Department(
        dept_id="001",
        name="Test Department",
        is_active=True
    )
    db.add(dept)
    await db.flush()
    
    employee = Employee(
        employee_id=f"{emp_id:05d}",
        first_name="Test",
        last_name="Employee",
        email=f"emp{emp_id}@test.com",
        department_id=dept.id,
        paid_leave_per_year=10,
        is_active=True
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


async def test_wage_config_creation():
    """Test wage configuration creation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        
        config = await WageCalculationService.get_or_create_wage_config(
            db, 
            employee_id=employee.id,
            hourly_rate=500.0,
            overtime_multiplier=1.5,
            night_shift_multiplier=1.5
        )
        
        assert config.employee_id == employee.id
        assert config.hourly_rate == 500.0
        assert config.overtime_multiplier == 1.5
        assert config.night_shift_multiplier == 1.5
        assert config.is_part_time == True
        
        print("✅ Wage config creation test passed")
    
    await teardown_test_db()


async def test_payroll_cycle_creation():
    """Test payroll cycle creation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        start_date = date(2025, 1, 1)
        cycle = await WageCalculationService.get_payroll_cycle(db, start_date)
        
        assert cycle.start_date == start_date
        assert cycle.end_date == date(2025, 1, 15)
        assert cycle.cycle_number == 1
        assert cycle.year == 2025
        assert cycle.is_closed == False
        assert cycle.is_confirmed == False
        
        print("✅ Payroll cycle creation test passed")
    
    await teardown_test_db()


async def test_wage_calculation_basic():
    """Test basic wage calculation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        
        # Setup wage config
        config = await WageCalculationService.get_or_create_wage_config(
            db,
            employee_id=employee.id,
            hourly_rate=500.0,
            overtime_multiplier=1.5,
            night_shift_multiplier=1.5
        )
        
        # Create payroll cycle
        start_date = date(2025, 1, 1)
        cycle = await WageCalculationService.get_payroll_cycle(db, start_date)
        
        # Create attendance record (8 hours regular work)
        attendance = Attendance(
            employee_id=employee.id,
            date=date(2025, 1, 1),
            in_time="09:00",
            out_time="17:00",
            worked_hours=8.0,
            overtime_hours=0.0,
            night_hours=0.0,
            break_minutes=60,
            status="onTime"
        )
        db.add(attendance)
        await db.commit()
        
        # Calculate wage
        wage_calc = await WageCalculationService.calculate_wage_for_period(
            db, employee.id, cycle
        )
        
        # Expected: 8 hours * 500 = 4000
        assert wage_calc.regular_hours == 8.0
        assert wage_calc.overtime_hours == 0.0
        assert wage_calc.night_hours == 0.0
        assert wage_calc.base_wage == 4000.0
        assert wage_calc.net_wage == 4000.0
        
        print("✅ Basic wage calculation test passed")
        print(f"   Regular hours: {wage_calc.regular_hours}")
        print(f"   Base wage: {wage_calc.base_wage}")
        print(f"   Net wage: {wage_calc.net_wage}")
    
    await teardown_test_db()


async def test_wage_calculation_with_overtime():
    """Test wage calculation with overtime"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        
        # Setup wage config
        config = await WageCalculationService.get_or_create_wage_config(
            db,
            employee_id=employee.id,
            hourly_rate=500.0,
            overtime_multiplier=1.5,
            night_shift_multiplier=1.5
        )
        
        # Create payroll cycle
        start_date = date(2025, 1, 1)
        cycle = await WageCalculationService.get_payroll_cycle(db, start_date)
        
        # Create attendance record (10 hours: 8 regular + 2 overtime)
        attendance = Attendance(
            employee_id=employee.id,
            date=date(2025, 1, 1),
            in_time="09:00",
            out_time="19:00",
            worked_hours=10.0,
            overtime_hours=2.0,
            night_hours=0.0,
            break_minutes=60,
            status="onTime"
        )
        db.add(attendance)
        await db.commit()
        
        # Calculate wage
        wage_calc = await WageCalculationService.calculate_wage_for_period(
            db, employee.id, cycle
        )
        
        # Expected: 8*500 + 2*500*1.5 = 4000 + 1500 = 5500
        assert wage_calc.regular_hours == 8.0
        assert wage_calc.overtime_hours == 2.0
        assert wage_calc.base_wage == 4000.0
        assert wage_calc.overtime_wage == 1500.0
        assert wage_calc.net_wage == 5500.0
        
        print("✅ Wage calculation with overtime test passed")
        print(f"   Regular hours: {wage_calc.regular_hours}")
        print(f"   Overtime hours: {wage_calc.overtime_hours}")
        print(f"   Base wage: {wage_calc.base_wage}")
        print(f"   Overtime wage: {wage_calc.overtime_wage}")
        print(f"   Net wage: {wage_calc.net_wage}")
    
    await teardown_test_db()


async def test_wage_calculation_with_night_shift():
    """Test wage calculation with night shift"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        
        # Setup wage config
        config = await WageCalculationService.get_or_create_wage_config(
            db,
            employee_id=employee.id,
            hourly_rate=500.0,
            overtime_multiplier=1.5,
            night_shift_multiplier=1.5
        )
        
        # Create payroll cycle
        start_date = date(2025, 1, 1)
        cycle = await WageCalculationService.get_payroll_cycle(db, start_date)
        
        # Create attendance record (22:00-06:00, 8 hours all night)
        attendance = Attendance(
            employee_id=employee.id,
            date=date(2025, 1, 1),
            in_time="22:00",
            out_time="06:00",
            worked_hours=8.0,
            overtime_hours=0.0,
            night_hours=8.0,
            break_minutes=0,
            status="onTime"
        )
        db.add(attendance)
        await db.commit()
        
        # Calculate wage
        wage_calc = await WageCalculationService.calculate_wage_for_period(
            db, employee.id, cycle
        )
        
        # Expected: 8*500*1.5 = 6000 (all night shift)
        assert wage_calc.regular_hours == 0.0
        assert wage_calc.night_hours == 8.0
        assert wage_calc.night_shift_wage == 6000.0
        assert wage_calc.net_wage == 6000.0
        
        print("✅ Wage calculation with night shift test passed")
        print(f"   Night hours: {wage_calc.night_hours}")
        print(f"   Night shift wage: {wage_calc.night_shift_wage}")
        print(f"   Net wage: {wage_calc.net_wage}")
    
    await teardown_test_db()


async def test_cycle_closure_and_confirmation():
    """Test payroll cycle closure and wage confirmation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        
        # Setup wage config
        config = await WageCalculationService.get_or_create_wage_config(
            db,
            employee_id=employee.id,
            hourly_rate=500.0
        )
        
        # Create cycle and wage calculation
        start_date = date(2025, 1, 1)
        cycle = await WageCalculationService.get_payroll_cycle(db, start_date)
        
        attendance = Attendance(
            employee_id=employee.id,
            date=date(2025, 1, 1),
            in_time="09:00",
            out_time="17:00",
            worked_hours=8.0,
            break_minutes=60,
            status="onTime"
        )
        db.add(attendance)
        await db.commit()
        
        wage_calc = await WageCalculationService.calculate_wage_for_period(
            db, employee.id, cycle
        )
        
        # Test cycle closure
        closure_result = await WageCalculationService.verify_and_close_cycle(db, cycle)
        
        assert closure_result['closing_status'] == 'success'
        assert closure_result['verified_employees'] > 0
        
        # Verify cycle is closed
        from sqlalchemy import select
        cycle_result = await db.execute(select(PayrollCycle).where(PayrollCycle.id == cycle.id))
        updated_cycle = cycle_result.scalar_one()
        assert updated_cycle.is_closed == True
        
        print("✅ Cycle closure test passed")
        print(f"   Closure status: {closure_result['closing_status']}")
        print(f"   Verified employees: {closure_result['verified_employees']}")
    
    await teardown_test_db()


async def run_all_tests():
    """Run all wage calculation tests"""
    print("\n" + "="*60)
    print("WAGE CALCULATION TESTS")
    print("="*60)
    
    try:
        await test_wage_config_creation()
        await test_payroll_cycle_creation()
        await test_wage_calculation_basic()
        await test_wage_calculation_with_overtime()
        await test_wage_calculation_with_night_shift()
        await test_cycle_closure_and_confirmation()
        
        print("\n" + "="*60)
        print("✅ ALL WAGE CALCULATION TESTS PASSED")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
