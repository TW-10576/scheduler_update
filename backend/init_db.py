"""
Database Initialization Script - Clean Start
Creates all tables and initializes with admin user only (no sample data)
Run: python init_db.py
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import DATABASE_URL
from app.models import Base, User, UserType
from app.auth import get_password_hash

async def init_database():
    print("🔄 Connecting to database...")
    engine = create_async_engine(DATABASE_URL, echo=False)

    print("📋 Creating all tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    print("✅ All tables created!")

    # Import session maker
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("👤 Initializing admin user...")

    async with async_session() as session:
        # Create Admin User only
        admin = User(
            username="admin",
            email="admin@company.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            user_type=UserType.ADMIN,
            is_active=True
        )
        session.add(admin)
        await session.commit()

    print("✅ Database initialized!")
    print("\n📊 Created:")
    print("   ✓ All database tables (empty - cold start)")
    print("   ✓ 1 Admin user")
    print("\n🚀 Ready for testing!")
    print("\n🔐 Admin Login:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n📝 Next Steps:")
    print("   1. Login as admin")
    print("   2. Create departments")
    print("   3. Create managers and assign to departments")
    print("   4. Create roles and shifts")
    print("   5. Create employees")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_database())
