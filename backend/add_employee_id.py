"""
Add employee_id column to employees table
Run: python add_employee_id.py
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.database import DATABASE_URL

async def add_employee_id_column():
    print("🔄 Connecting to database...")
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        try:
            # Check if column already exists
            result = await conn.execute(
                text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name='employees' AND column_name='employee_id'
                """)
            )
            
            if result.fetchone():
                print("✅ Column employee_id already exists!")
            else:
                print("📝 Adding employee_id column...")
                await conn.execute(
                    text("""
                        ALTER TABLE employees 
                        ADD COLUMN employee_id VARCHAR(10)
                    """)
                )
                print("✅ Column employee_id added!")
                
                # Update existing employees with auto-generated IDs
                print("📝 Generating employee IDs...")
                await conn.execute(
                    text("""
                        UPDATE employees 
                        SET employee_id = LPAD(id::text, 5, '0')
                        WHERE employee_id IS NULL
                    """)
                )
                print("✅ Employee IDs generated!")
                
                # Make it unique and not null
                print("📝 Adding constraints...")
                await conn.execute(
                    text("""
                        ALTER TABLE employees 
                        ALTER COLUMN employee_id SET NOT NULL
                    """)
                )
                await conn.execute(
                    text("""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_employee_id 
                        ON employees(employee_id)
                    """)
                )
                print("✅ Constraints added!")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            raise
    
    await engine.dispose()
    print("✅ Migration complete!")

if __name__ == "__main__":
    asyncio.run(add_employee_id_column())
