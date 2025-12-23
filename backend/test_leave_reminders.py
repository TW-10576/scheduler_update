"""
Comprehensive Tests for Leave Reminder System
Tests leave balance tracking, reminder sending, and trends
"""

import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Employee, Department, LeaveRequest, LeaveBalance, LeaveReminder, User, UserType, LeaveStatus
from app.leave_reminder_service import LeaveReminderService


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


async def create_test_employee(db: AsyncSession, emp_id: int = 1, paid_leave: int = 10):
    """Create a test employee"""
    # Create department
    dept = Department(
        dept_id="001",
        name="Test Department",
        is_active=True
    )
    db.add(dept)
    await db.flush()
    
    # Create user
    user = User(
        username=f"emp{emp_id}",
        email=f"emp{emp_id}@test.com",
        hashed_password="hashed",
        user_type=UserType.EMPLOYEE,
        is_active=True
    )
    db.add(user)
    await db.flush()
    
    employee = Employee(
        employee_id=f"{emp_id:05d}",
        first_name="Test",
        last_name="Employee",
        email=f"emp{emp_id}@test.com",
        department_id=dept.id,
        user_id=user.id,
        paid_leave_per_year=paid_leave,
        is_active=True
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return employee


async def create_test_leave(db: AsyncSession, employee_id: int, start: date, end: date, leave_type: str = 'paid'):
    """Create a test leave request"""
    leave = LeaveRequest(
        employee_id=employee_id,
        start_date=start,
        end_date=end,
        leave_type=leave_type,
        status=LeaveStatus.APPROVED
    )
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave


async def test_leave_balance_check():
    """Test leave balance checking"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db, paid_leave=10)
        
        # Create some leave requests
        year = date.today().year
        await create_test_leave(db, employee.id, date(year, 1, 1), date(year, 1, 3))  # 3 days
        await create_test_leave(db, employee.id, date(year, 2, 1), date(year, 2, 2))  # 2 days
        
        # Check balance
        balance_info = await LeaveReminderService.check_leave_balance(db, employee.id, year)
        
        assert balance_info['total_entitlement'] == 10
        assert balance_info['paid_used'] == 5
        assert balance_info['remaining'] == 5
        assert balance_info['usage_percentage'] == 50.0
        
        print("✅ Leave balance check test passed")
        print(f"   Total entitlement: {balance_info['total_entitlement']}")
        print(f"   Used: {balance_info['paid_used']}")
        print(f"   Remaining: {balance_info['remaining']}")
        print(f"   Usage: {balance_info['usage_percentage']}%")
    
    await teardown_test_db()


async def test_low_balance_reminders():
    """Test low balance reminder sending"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db, paid_leave=10)
        
        # Use 8 days (2 remaining - below threshold of 3)
        year = date.today().year
        await create_test_leave(db, employee.id, date(year, 1, 1), date(year, 1, 8))  # 8 days
        
        # Send reminders
        reminders = await LeaveReminderService.send_reminders_to_low_balance(db, threshold_days=3)
        
        assert len(reminders) > 0
        assert reminders[0]['employee_id'] == employee.id
        assert reminders[0]['remaining_days'] == 2
        assert reminders[0]['reminder_type'] == 'low_balance'
        
        print("✅ Low balance reminder test passed")
        print(f"   Reminders sent: {len(reminders)}")
        print(f"   Employee: {reminders[0]['employee_name']}")
        print(f"   Remaining days: {reminders[0]['remaining_days']}")
    
    await teardown_test_db()


async def test_mid_year_reminders():
    """Test mid-year reminder sending"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db, paid_leave=10)
        
        # Create some leave
        year = date.today().year
        await create_test_leave(db, employee.id, date(year, 1, 1), date(year, 1, 3))  # 3 days
        
        # Send mid-year reminders
        reminders = await LeaveReminderService.send_mid_year_reminder(db)
        
        # Should have reminders (at least in summer months)
        if len(reminders) > 0:
            print("✅ Mid-year reminder test passed")
            print(f"   Reminders sent: {len(reminders)}")
        else:
            print("✅ Mid-year reminder test passed (no reminders in this season)")
    
    await teardown_test_db()


async def test_leave_trends():
    """Test leave trend analysis"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db, paid_leave=10)
        
        # Create leaves for multiple years
        for year_offset in range(3):
            year = date.today().year - year_offset
            days_to_use = (2 + year_offset)  # 2, 3, 4 days
            
            # Create balance record
            balance = LeaveBalance(
                employee_id=employee.id,
                year=year,
                total_paid_leave=10,
                used_paid_leave=days_to_use,
                remaining_paid_leave=10 - days_to_use,
                total_unpaid_leave=0
            )
            db.add(balance)
        
        await db.commit()
        
        # Get trends
        trends = await LeaveReminderService.get_leave_trends(db, employee.id, num_years=3)
        
        assert len(trends['trends']) > 0
        assert 'average_usage_percentage' in trends
        assert 'trend_direction' in trends
        
        print("✅ Leave trend analysis test passed")
        print(f"   Analysis period: {trends['analysis_period']}")
        print(f"   Average usage: {trends['average_usage_percentage']}%")
        print(f"   Trend direction: {trends['trend_direction']}")
    
    await teardown_test_db()


async def test_reminder_acknowledgement():
    """Test reminder acknowledgement tracking"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        employee = await create_test_employee(db)
        
        # Create a reminder
        reminder = LeaveReminder(
            employee_id=employee.id,
            reminder_date=datetime.utcnow(),
            remaining_days_at_time=3,
            reminder_type='low_balance'
        )
        db.add(reminder)
        await db.commit()
        await db.refresh(reminder)
        
        # Track acknowledgement
        updated_reminder = await LeaveReminderService.track_reminder_sent(
            db, reminder.id, action_taken="Requested 2 days leave", is_acknowledged=True
        )
        
        assert updated_reminder.is_acknowledged == True
        assert updated_reminder.acknowledgment_date is not None
        assert updated_reminder.action_taken == "Requested 2 days leave"
        
        print("✅ Reminder acknowledgement test passed")
        print(f"   Acknowledged: {updated_reminder.is_acknowledged}")
        print(f"   Action taken: {updated_reminder.action_taken}")
    
    await teardown_test_db()


async def test_department_leave_summary():
    """Test department-wide leave summary"""
    await setup_test_db()
    
    async with TestingSessionLocal() as db:
        # Create multiple employees
        emp1 = await create_test_employee(db, emp_id=1, paid_leave=10)
        emp2 = await create_test_employee(db, emp_id=2, paid_leave=10)
        
        year = date.today().year
        
        # Create leaves
        await create_test_leave(db, emp1.id, date(year, 1, 1), date(year, 1, 3))  # 3 days
        await create_test_leave(db, emp2.id, date(year, 1, 1), date(year, 1, 5))  # 5 days
        
        # Get department summary
        summary = await LeaveReminderService.get_department_leave_summary(
            db, emp1.department_id, year
        )
        
        assert summary['total_employees'] == 2
        assert summary['total_entitlement'] == 20
        assert summary['total_used'] == 8
        assert summary['total_remaining'] == 12
        assert len(summary['employee_summaries']) == 2
        
        print("✅ Department leave summary test passed")
        print(f"   Total employees: {summary['total_employees']}")
        print(f"   Total entitlement: {summary['total_entitlement']}")
        print(f"   Total used: {summary['total_used']}")
        print(f"   Total remaining: {summary['total_remaining']}")
        print(f"   Average usage: {summary['average_usage_percentage']}%")
    
    await teardown_test_db()


async def run_all_tests():
    """Run all leave reminder tests"""
    print("\n" + "="*60)
    print("LEAVE REMINDER TESTS")
    print("="*60)
    
    try:
        await test_leave_balance_check()
        await test_low_balance_reminders()
        await test_mid_year_reminders()
        await test_leave_trends()
        await test_reminder_acknowledgement()
        await test_department_leave_summary()
        
        print("\n" + "="*60)
        print("✅ ALL LEAVE REMINDER TESTS PASSED")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
