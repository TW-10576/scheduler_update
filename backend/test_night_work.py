"""
Comprehensive Tests for Night Work and Attendance
Tests late-night work detection and attendance data aggregation
"""

import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Employee, Department, Attendance, LateNightWork, AttendanceSummary
from app.attendance_service import AttendanceService


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
    # Create department
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
        is_active=True
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


async def test_night_work_calculation():
    """Test night work hours calculation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        # Test 1: Normal day shift (no night hours)
        night_hours = await AttendanceService.calculate_night_work_hours("09:00", "17:00")
        assert night_hours == 0.0, f"Expected 0, got {night_hours}"
        print(f"✓ Day shift (09:00-17:00): {night_hours} hours")
        
        # Test 2: Evening to late night (22:00-23:00 is 1 hour)
        night_hours = await AttendanceService.calculate_night_work_hours("21:00", "23:00")
        assert night_hours == 1.0, f"Expected 1, got {night_hours}"
        print(f"✓ Evening to late night (21:00-23:00): {night_hours} hours")
        
        # Test 3: Full night shift (22:00-06:00 is 8 hours)
        night_hours = await AttendanceService.calculate_night_work_hours("22:00", "06:00")
        assert night_hours == 8.0, f"Expected 8, got {night_hours}"
        print(f"✓ Full night shift (22:00-06:00): {night_hours} hours")
        
        # Test 4: Partial night (23:00-05:00 is 6 hours)
        night_hours = await AttendanceService.calculate_night_work_hours("23:00", "05:00")
        assert night_hours == 6.0, f"Expected 6, got {night_hours}"
        print(f"✓ Partial night (23:00-05:00): {night_hours} hours")
        
        # Test 5: Late evening (18:00-22:00 is 0 hours - before night period)
        night_hours = await AttendanceService.calculate_night_work_hours("18:00", "22:00")
        assert night_hours == 0.0, f"Expected 0, got {night_hours}"
        print(f"✓ Late evening (18:00-22:00): {night_hours} hours")
        
        print("✅ Night work calculation test passed\n")
    
    await teardown_test_db()


async def test_overtime_vs_night_calculation():
    """Test distinguishing between overtime and night work"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        # Test 1: 8 hours day shift (09:00-17:00 = 8 hrs, minus 1 hr break = 7 hrs worked)
        regular, overtime, night = await AttendanceService.calculate_overtime_vs_night(
            "09:00", "17:00", scheduled_hours=8.0, break_minutes=60
        )
        assert overtime == 0.0 and night == 0.0
        print(f"✓ Day shift: Regular={regular}, OT={overtime}, Night={night}")
        
        # Test 2: 10 hours day shift (09:00-19:00 = 10 hrs, minus 1 hr break = 9 hrs, so 1 hr OT)
        regular, overtime, night = await AttendanceService.calculate_overtime_vs_night(
            "09:00", "19:00", scheduled_hours=8.0, break_minutes=60
        )
        assert overtime == 1.0 and night == 0.0
        print(f"✓ Day + OT: Regular={regular}, OT={overtime}, Night={night}")
        
        # Test 3: Night shift (20:00-06:00 next day, no break)
        regular, overtime, night = await AttendanceService.calculate_overtime_vs_night(
            "20:00", "06:00", scheduled_hours=8.0, break_minutes=0
        )
        assert night > 0
        print(f"✓ Night shift: Regular={regular}, OT={overtime}, Night={night}")
        
        print("✅ Overtime vs night calculation test passed\n")
    
    await teardown_test_db()


async def test_worked_hours_calculation():
    """Test worked hours calculation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        # Test 1: 8 hours with 1 hour break
        hours = await AttendanceService.calculate_worked_hours("09:00", "18:00", break_minutes=60)
        assert hours == 8.0, f"Expected 8, got {hours}"
        print(f"✓ 09:00-18:00 (1hr break): {hours} hours")
        
        # Test 2: 10 hours with no break
        hours = await AttendanceService.calculate_worked_hours("09:00", "19:00", break_minutes=0)
        assert hours == 10.0, f"Expected 10, got {hours}"
        print(f"✓ 09:00-19:00 (no break): {hours} hours")
        
        # Test 3: 8 hours across midnight
        hours = await AttendanceService.calculate_worked_hours("22:00", "06:00", break_minutes=0)
        assert hours == 8.0, f"Expected 8, got {hours}"
        print(f"✓ 22:00-06:00 (next day): {hours} hours")
        
        print("✅ Worked hours calculation test passed\n")
    
    await teardown_test_db()


async def test_attendance_summary_aggregation():
    """Test attendance summary aggregation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        month_start = date(2025, 1, 1)
        
        # Create several attendance records for the month
        for day in range(1, 6):  # First 5 working days
            attendance = Attendance(
                employee_id=employee.id,
                date=date(2025, 1, day),
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
        
        # Get monthly summary
        summary = await AttendanceService.aggregate_attendance_summary(
            db, employee.id, 'monthly', month_start
        )
        
        assert summary['days_worked'] == 5
        assert summary['total_worked_hours'] == 40.0
        assert summary['on_time_count'] == 5
        assert summary['on_time_percentage'] == 100.0
        
        print("✅ Attendance summary aggregation test passed")
        print(f"   Days worked: {summary['days_worked']}")
        print(f"   Total hours: {summary['total_worked_hours']}")
        print(f"   On-time %: {summary['on_time_percentage']}%\n")
    
    await teardown_test_db()


async def test_attendance_validation():
    """Test attendance data validation"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        
        # Create valid record
        valid = Attendance(
            employee_id=employee.id,
            date=date(2025, 1, 1),
            in_time="09:00",
            out_time="17:00",
            worked_hours=8.0,
            status="onTime"
        )
        db.add(valid)
        
        # Create invalid record (missing out_time)
        invalid = Attendance(
            employee_id=employee.id,
            date=date(2025, 1, 2),
            in_time="09:00",
            out_time=None,
            worked_hours=0.0,
            status="onTime"
        )
        db.add(invalid)
        
        await db.commit()
        
        # Validate
        validation = await AttendanceService.validate_attendance_data(
            db, employee.id, date(2025, 1, 1), date(2025, 1, 31)
        )
        
        assert validation['total_records'] == 2
        assert validation['records_with_issues'] == 1
        assert len(validation['issues']) > 0
        
        print("✅ Attendance validation test passed")
        print(f"   Total records: {validation['total_records']}")
        print(f"   Records with issues: {validation['records_with_issues']}")
        print(f"   Valid: {validation['is_valid']}\n")
    
    await teardown_test_db()


async def test_create_or_update_summary():
    """Test creating/updating attendance summary records"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        month_start = date(2025, 1, 1)
        
        # Create attendance records
        for day in range(1, 4):
            attendance = Attendance(
                employee_id=employee.id,
                date=date(2025, 1, day),
                in_time="09:00",
                out_time="17:00",
                worked_hours=8.0,
                break_minutes=60,
                status="onTime"
            )
            db.add(attendance)
        
        await db.commit()
        
        # Create summary
        summary_record = await AttendanceService.create_or_update_attendance_summary(
            db, employee.id, 'monthly', month_start
        )
        
        assert summary_record.employee_id == employee.id
        assert summary_record.period_type == 'monthly'
        assert summary_record.days_worked == 3
        assert summary_record.total_worked_hours == 24.0
        
        print("✅ Create/update summary test passed")
        print(f"   Summary ID: {summary_record.id}")
        print(f"   Days worked: {summary_record.days_worked}")
        print(f"   Total hours: {summary_record.total_worked_hours}\n")
    
    await teardown_test_db()


async def run_all_tests():
    """Run all night work and attendance tests"""
    print("\n" + "="*60)
    print("NIGHT WORK & ATTENDANCE TESTS")
    print("="*60 + "\n")
    
    try:
        await test_night_work_calculation()
        await test_overtime_vs_night_calculation()
        await test_worked_hours_calculation()
        await test_attendance_summary_aggregation()
        await test_attendance_validation()
        await test_create_or_update_summary()
        
        print("="*60)
        print("✅ ALL NIGHT WORK & ATTENDANCE TESTS PASSED")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
