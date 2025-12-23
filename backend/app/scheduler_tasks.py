"""
Scheduler for Automated Tasks
- Leave reminder checks (daily)
- Payroll cycle processing (weekly)
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timedelta
import asyncio
import logging

from app.database import AsyncSessionLocal
from app.leave_reminder_service import LeaveReminderService
from app.wage_calculation_service import WageCalculationService
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def check_leave_reminders_job():
    """Daily job to check and send leave balance reminders"""
    try:
        async with AsyncSessionLocal() as db:
            logger.info("Running leave reminder check...")
            
            # Send low balance reminders (< 3 days)
            reminders = await LeaveReminderService.send_reminders_to_low_balance(db, threshold_days=3)
            logger.info(f"Sent {len(reminders)} low balance reminders")
            
            # Check if it's mid-year (June/July) - send mid-year reminders
            today = date.today()
            if today.month in [6, 7]:
                mid_year_reminders = await LeaveReminderService.send_mid_year_reminder(db)
                logger.info(f"Sent {len(mid_year_reminders)} mid-year reminders")
            
            # Check if it's year-end (November/December) - send year-end reminders
            if today.month in [11, 12]:
                year_end_reminders = await LeaveReminderService.send_year_end_reminder(db)
                logger.info(f"Sent {len(year_end_reminders)} year-end reminders")
    
    except Exception as e:
        logger.error(f"Error in leave reminder job: {str(e)}")


async def process_payroll_cycles_job():
    """Weekly job to process payroll cycles (runs on Sundays)"""
    try:
        async with AsyncSessionLocal() as db:
            logger.info("Running payroll cycle processing...")
            
            # Process latest cycle
            today = date.today()
            # Find the 15-day cycle that ended today or recently
            cycle_start = today - timedelta(days=today.day % 15)  # Approximate start of current cycle
            
            from app.models import PayrollCycle
            from sqlalchemy import select
            
            cycle_result = await db.execute(
                select(PayrollCycle).where(
                    PayrollCycle.start_date <= today,
                    PayrollCycle.end_date >= today
                )
            )
            cycle = cycle_result.scalar_one_or_none()
            
            if cycle and not cycle.is_closed:
                logger.info(f"Processing cycle {cycle.cycle_number}...")
                
                # Verify and close the cycle
                result = await WageCalculationService.verify_and_close_cycle(db, cycle)
                logger.info(f"Cycle closing result: {result}")
    
    except Exception as e:
        logger.error(f"Error in payroll processing job: {str(e)}")


def start_scheduler():
    """Start the async scheduler"""
    try:
        # Daily leave reminder check at 9:00 AM
        scheduler.add_job(
            check_leave_reminders_job,
            CronTrigger(hour=9, minute=0),
            id='leave_reminders',
            name='Daily leave reminder check'
        )
        
        # Weekly payroll processing on Sundays at 10:00 AM
        scheduler.add_job(
            process_payroll_cycles_job,
            CronTrigger(day_of_week=6, hour=10, minute=0),  # Sunday = 6
            id='payroll_processing',
            name='Weekly payroll cycle processing'
        )
        
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")


def stop_scheduler():
    """Stop the scheduler"""
    try:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
