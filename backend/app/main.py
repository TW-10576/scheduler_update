"""
FastAPI Main Application - Shift Scheduler V5.1
Complete with Employee Portal, Messaging, and Check-In/Out
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse, StreamingResponse
import io
from calendar import monthrange
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, func, Float
from sqlalchemy.orm import selectinload, with_loader_criteria
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional
from collections import defaultdict

from ortools.sat.python import cp_model

from app.config import settings
from app.database import get_db
from app.models import (
    User, Department, Manager, Employee, Role, Schedule, LeaveRequest,
    CheckInOut, Message, Notification,
    UserType, LeaveStatus, Attendance, Unavailability, Shift
)
from app.schemas import *
from app.auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user, require_admin, require_manager, require_employee
)
from app.schedule_generator import ShiftScheduleGenerator

app = FastAPI(
    title="Shift Scheduler V5.1 API",
    description="Complete Employee Portal with Check-In/Out and Messaging",
    version="5.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler for HTTPException to include CORS headers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    origin = request.headers.get("origin")
    cors_origins = [str(o) for o in settings.CORS_ORIGINS]
    
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
    
    # Add CORS headers if origin is allowed
    if origin in cors_origins or "*" in cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin or "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    
    return response


# Health check
@app.get("/")
async def root():
    return {
        "message": "Shift Scheduler V5.1 API",
        "version": "5.1.0",
        "status": "running",
        "features": ["employee-portal", "messaging", "check-in-out", "leave-approval"]
    }


# Authentication
@app.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Get manager info if user is a manager
    manager_department_id = None
    if user.user_type == UserType.MANAGER:
        result = await db.execute(select(Manager).filter(Manager.user_id == user.id))
        manager = result.scalar_one_or_none()
        if manager:
            manager_department_id = manager.department_id
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "user_type": user.user_type,
            "manager_department_id": manager_department_id
        }
    }


@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# Admin: User Management
@app.post("/admin/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    # Check if username exists
    result = await db.execute(select(User).filter(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        user_type=user_data.user_type,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return new_user


@app.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User))
    return result.scalars().all()


@app.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user (admin, manager, or employee)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If deleting a manager, delete the manager record
    if user.user_type == UserType.MANAGER:
        result = await db.execute(
            select(Manager).filter(Manager.user_id == user_id)
        )
        manager = result.scalar_one_or_none()
        if manager:
            await db.delete(manager)
    
    await db.delete(user)
    await db.commit()
    
    return {"message": f"User {user.username} deleted successfully"}


# Departments
@app.post("/departments", response_model=DepartmentResponse)
async def create_department(
    dept_data: DepartmentCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    # Use provided dept_id or auto-generate if not provided
    dept_id_to_use = dept_data.dept_id.strip() if hasattr(dept_data, 'dept_id') and dept_data.dept_id else None
    
    if not dept_id_to_use:
        # Auto-generate dept_id (001, 002, 003, etc.)
        result = await db.execute(
            select(Department).order_by(Department.id.desc()).limit(1)
        )
        last_dept = result.scalar_one_or_none()
        next_id = 1
        if last_dept and last_dept.dept_id.isdigit():
            next_id = int(last_dept.dept_id) + 1
        dept_id_to_use = str(next_id).zfill(3)
    
    department = Department(
        dept_id=dept_id_to_use,
        name=dept_data.name,
        description=dept_data.description,
        is_active=True
    )
    
    db.add(department)
    await db.commit()
    await db.refresh(department)
    
    return department


@app.put("/departments/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    dept_data: DepartmentCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Department).filter(Department.id == department_id))
    department = result.scalar_one_or_none()
    
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    department.name = dept_data.name
    department.description = dept_data.description
    department.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(department)
    
    return department


@app.get("/departments", response_model=List[DepartmentResponse])
async def list_departments(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # All authenticated users can view active departments
    result = await db.execute(select(Department).filter(Department.is_active == True))
    return result.scalars().all()


@app.get("/departments/{department_id}/details", response_model=DepartmentDetailResponse)
async def get_department_details(
    department_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get department details with manager and employees + attendance info"""
    # Get department
    dept_result = await db.execute(
        select(Department).filter(Department.id == department_id)
    )
    department = dept_result.scalar_one_or_none()
    
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Get manager for this department
    mgr_result = await db.execute(
        select(Manager).filter(Manager.department_id == department_id)
    )
    manager = mgr_result.scalar_one_or_none()
    manager_info = None
    if manager:
        user_result = await db.execute(
            select(User).filter(User.id == manager.user_id)
        )
        manager_user = user_result.scalar_one_or_none()
        if manager_user:
            manager_info = {
                "id": manager.id,
                "user_id": manager.user_id,
                "username": manager_user.username,
                "full_name": manager_user.full_name,
                "email": manager_user.email
            }
    
    # Get all employees in this department
    emp_result = await db.execute(
        select(Employee).filter(
            Employee.department_id == department_id,
            Employee.is_active == True
        ).order_by(Employee.id)
    )
    employees = emp_result.scalars().all()
    
    # Get latest attendance for each employee
    employee_list = []
    for emp in employees:
        # Get latest check-in/out
        checkin_result = await db.execute(
            select(CheckInOut).filter(
                CheckInOut.employee_id == emp.id
            ).order_by(CheckInOut.date.desc(), CheckInOut.check_in_time.desc()).limit(1)
        )
        latest_checkin = checkin_result.scalar_one_or_none()
        
        employee_list.append({
            "id": emp.id,
            "employee_id": emp.employee_id,
            "first_name": emp.first_name,
            "last_name": emp.last_name,
            "email": emp.email,
            "latest_check_in": latest_checkin.check_in_time if latest_checkin else None,
            "latest_check_out": latest_checkin.check_out_time if latest_checkin else None
        })
    
    return {
        "id": department.id,
        "dept_id": department.dept_id,
        "name": department.name,
        "description": department.description,
        "manager": manager_info,
        "employees": employee_list
    }


@app.delete("/departments/{department_id}")
async def delete_department(
    department_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete a department and all related data"""
    result = await db.execute(select(Department).filter(Department.id == department_id))
    department = result.scalar_one_or_none()
    
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    dept_name = department.name
    
    # Delete all employees in the department (cascade will handle schedules, leave requests, check-ins)
    result = await db.execute(
        select(Employee).filter(Employee.department_id == department_id)
    )
    employees = result.scalars().all()
    for employee in employees:
        await db.delete(employee)
    
    # Delete all roles in the department (cascade will handle schedules)
    result = await db.execute(
        select(Role).filter(Role.department_id == department_id)
    )
    roles = result.scalars().all()
    for role in roles:
        await db.delete(role)
    
    # Delete all schedules in the department
    result = await db.execute(
        select(Schedule).filter(Schedule.department_id == department_id)
    )
    schedules = result.scalars().all()
    for schedule in schedules:
        await db.delete(schedule)
    
    # Delete the department itself
    await db.delete(department)
    await db.commit()
    
    return {"message": f"Department {dept_name} and all related data deleted successfully"}


@app.get("/departments/search/{query}")
async def search_departments(
    query: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Search departments by ID, dept_id, or name"""
    # Try to search by internal ID first (if query is numeric)
    try:
        dept_id = int(query)
        result = await db.execute(
            select(Department).filter(
                Department.id == dept_id,
                Department.is_active == True
            )
        )
        department = result.scalar_one_or_none()
        if department:
            return {
                "id": department.id,
                "dept_id": department.dept_id,
                "name": department.name,
                "description": department.description
            }
    except ValueError:
        pass
    
    # Try to search by dept_id (3-digit code like 001, 002, etc.)
    result = await db.execute(
        select(Department).filter(
            Department.dept_id == query.zfill(3),
            Department.is_active == True
        )
    )
    department = result.scalar_one_or_none()
    if department:
        return {
            "id": department.id,
            "dept_id": department.dept_id,
            "name": department.name,
            "description": department.description
        }
    
    # Search by name (case-insensitive)
    result = await db.execute(
        select(Department).filter(
            Department.name.ilike(f"%{query}%"),
            Department.is_active == True
        )
    )
    departments = result.scalars().all()
    
    if departments:
        return [
            {
                "id": d.id,
                "dept_id": d.dept_id,
                "name": d.name,
                "description": d.description
            }
            for d in departments
        ]
    
    raise HTTPException(status_code=404, detail="Department not found")


# Managers
@app.post("/managers", response_model=dict)
async def create_manager(
    mgr_data: ManagerCreate,
    force_reassign: bool = False,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a manager and link to a department. If force_reassign=true, will replace existing manager."""
    # Check if user exists
    result = await db.execute(select(User).filter(User.id == mgr_data.user_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if department exists
    result = await db.execute(select(Department).filter(Department.id == mgr_data.department_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Check if another manager is already assigned to this department
    existing_result = await db.execute(
        select(Manager).filter(
            and_(
                Manager.department_id == mgr_data.department_id,
                Manager.is_active == True
            )
        ).options(selectinload(Manager.user))
    )
    existing_manager = existing_result.scalar_one_or_none()
    
    if existing_manager:
        if not force_reassign:
            # Return existing manager info for frontend confirmation
            return {
                "status": "conflict",
                "message": "Manager already assigned to this department",
                "action_required": "reassign",
                "existing_manager": {
                    "id": existing_manager.id,
                    "user_id": existing_manager.user_id,
                    "username": existing_manager.user.username if existing_manager.user else None,
                    "full_name": existing_manager.user.full_name if existing_manager.user else None,
                    "email": existing_manager.user.email if existing_manager.user else None,
                    "department_id": existing_manager.department_id,
                    "is_active": existing_manager.is_active
                },
                "new_manager": {
                    "user_id": mgr_data.user_id,
                    "department_id": mgr_data.department_id
                }
            }
        else:
            # Reassign: unassign old manager from this department (don't deactivate)
            existing_manager.department_id = None
            existing_manager.updated_at = datetime.utcnow()
            db.add(existing_manager)  # Ensure the change is tracked
    
    # Create new manager
    manager = Manager(**mgr_data.dict())
    db.add(manager)
    await db.commit()
    await db.refresh(manager)
    
    return {
        "status": "success",
        "message": "Manager assigned successfully",
        "manager": {
            "id": manager.id,
            "user_id": manager.user_id,
            "department_id": manager.department_id,
            "is_active": manager.is_active
        }
    }


@app.get("/managers", response_model=List[ManagerDetailResponse])
async def list_managers(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Manager)
        .filter(Manager.is_active == True)
        .options(selectinload(Manager.user))
    )
    managers = result.scalars().all()
    
    # Build response with user details
    response = []
    for manager in managers:
        user = manager.user
        response.append({
            'id': manager.id,
            'user_id': manager.user_id,
            'username': user.username if user else None,
            'full_name': user.full_name if user else None,
            'email': user.email if user else None,
            'department_id': manager.department_id,
            'is_active': manager.is_active,
        })

    return response


@app.put("/managers/{manager_id}", response_model=ManagerResponse)
async def update_manager(
    manager_id: int,
    mgr_data: ManagerCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Manager).filter(Manager.id == manager_id))
    manager = result.scalar_one_or_none()
    
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    # Check if another manager is already assigned to this department
    if mgr_data.department_id != manager.department_id:
        existing_result = await db.execute(
            select(Manager).filter(
                and_(
                    Manager.department_id == mgr_data.department_id,
                    Manager.is_active == True,
                    Manager.id != manager_id
                )
            )
        )
        existing_manager = existing_result.scalar_one_or_none()
        if existing_manager:
            raise HTTPException(
                status_code=409, 
                detail=f"Manager already assigned",
                headers={"X-Existing-Manager-Id": str(existing_manager.id)}
            )
    
    manager.department_id = mgr_data.department_id
    manager = mgr_data
    manager = mgr_data
    manager.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(manager)
    
    return manager


@app.put("/managers/{manager_id}/reassign", response_model=ManagerResponse)
async def reassign_manager(
    manager_id: int,
    mgr_data: ManagerCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Reassign a manager to a department, removing any existing manager from that department"""
    result = await db.execute(select(Manager).filter(Manager.id == manager_id))
    manager = result.scalar_one_or_none()
    
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    # If reassigning to a different department, unassign the existing manager
    if mgr_data.department_id != manager.department_id:
        existing_result = await db.execute(
            select(Manager).filter(
                and_(
                    Manager.department_id == mgr_data.department_id,
                    Manager.is_active == True,
                    Manager.id != manager_id
                )
            )
        )
        existing_manager = existing_result.scalar_one_or_none()
        if existing_manager:
            existing_manager.department_id = None
            existing_manager.updated_at = datetime.utcnow()
            db.add(existing_manager)  # Ensure the change is tracked
    
    manager.department_id = mgr_data.department_id
    manager = mgr_data
    manager = mgr_data
    manager.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(manager)
    
    return manager


@app.delete("/managers/{manager_id}")
async def delete_manager(
    manager_id: int,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Manager).filter(Manager.id == manager_id))
    manager = result.scalar_one_or_none()
    
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    await db.delete(manager)
    await db.commit()
    
    return {"message": "Manager deleted successfully"}


# Employees
@app.post("/employees", response_model=EmployeeResponse)
async def create_employee(
    emp_data: EmployeeCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    # Managers can only create in their department
    # Get the manager's department from Manager table
    result = await db.execute(select(Manager).filter(Manager.user_id == current_user.id))
    manager_record = result.scalar_one_or_none()
    
    if manager_record and emp_data.department_id != manager_record.department_id:
        raise HTTPException(status_code=403, detail="Can only create employees in your department")
    
    # Check if employee with this email already exists
    existing = await db.execute(select(Employee).filter(Employee.email == emp_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Employee with email {emp_data.email} already exists")

    # Generate numeric employee ID by extracting numbers from existing IDs
    result = await db.execute(select(Employee.employee_id))
    employee_ids = result.scalars().all()

    # Extract numeric parts from IDs like "EMP001", "EMP002", etc.
    max_num = 0
    for emp_id in employee_ids:
        if emp_id and len(emp_id) > 3:
            try:
                num = int(emp_id[3:])  # Extract numbers after "EMP"
                if num > max_num:
                    max_num = num
            except ValueError:
                pass

    new_employee_id = f"EMP{str(max_num + 1).zfill(3)}"  # Format as EMP001, EMP002, etc.

    # Create employee without user_id (optional)
    emp_dict = emp_data.dict(exclude={'password'})
    emp_dict['employee_id'] = new_employee_id
    employee = Employee(**emp_dict)
    db.add(employee)
    await db.flush()  # Get the employee ID
    
    # If password provided, create a user account
    if hasattr(emp_data, 'password') and emp_data.password:
        # Check if username already exists (use email as username)
        username = emp_data.email.split('@')[0]  # Use part before @ as username
        result = await db.execute(select(User).filter(User.username == username))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Username {username} already exists")
        
        user = User(
            username=username,
            email=emp_data.email,
            full_name=f"{emp_data.first_name} {emp_data.last_name}",
            hashed_password=get_password_hash(emp_data.password),
            user_type=UserType.EMPLOYEE,
            is_active=True
        )
        db.add(user)
        await db.flush()
        
        # Link employee to user
        employee.user_id = user.id
    
    await db.commit()
    await db.refresh(employee)
    
    return employee


@app.get("/employees", response_model=List[EmployeeResponse])
async def list_employees(
    current_user: User = Depends(get_current_active_user),
    show_inactive: bool = False,  # Query parameter to show inactive employees
    db: AsyncSession = Depends(get_db)
):
    filters = []

    if current_user.user_type == UserType.ADMIN:
        # Admin sees all employees in their departments
        if not show_inactive:
            filters.append(Employee.is_active == True)
        result = await db.execute(select(Employee).filter(*filters) if filters else select(Employee))
    elif current_user.user_type == UserType.MANAGER:
        # Get manager's department from Manager table
        manager_result = await db.execute(select(Manager).filter(Manager.user_id == current_user.id))
        manager = manager_result.scalar_one_or_none()

        if manager:
            filters.append(Employee.department_id == manager.department_id)
            if not show_inactive:
                filters.append(Employee.is_active == True)
            result = await db.execute(select(Employee).filter(*filters))
        else:
            # No manager record, return empty list
            result = await db.execute(
                select(Employee).filter(Employee.id == -1)  # Returns empty
            )
    else:  # Employee
        if not show_inactive:
            filters.append(Employee.is_active == True)
        filters.append(Employee.user_id == current_user.id)
        result = await db.execute(select(Employee).filter(*filters))

    return result.scalars().all()


@app.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    emp_data: EmployeeCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Employee).filter(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if current_user.user_type == UserType.MANAGER:
        # Get manager's department from Manager table
        manager_result = await db.execute(select(Manager).filter(Manager.user_id == current_user.id))
        manager = manager_result.scalar_one_or_none()
        
        if not manager or employee.department_id != manager.department_id:
            raise HTTPException(status_code=403, detail="Can only edit employees in your department")
    
    # Update employee fields (exclude password which needs special handling)
    emp_dict = emp_data.dict(exclude={'password'})
    for key, value in emp_dict.items():
        setattr(employee, key, value)
    
    # Handle password update if provided
    if emp_data.password:
        # Update user password if employee has a user account
        if employee.user_id:
            result = await db.execute(select(User).filter(User.id == employee.user_id))
            user = result.scalar_one_or_none()
            if user:
                user.hashed_password = get_password_hash(emp_data.password)
                # Ensure user is in the session
                db.add(user)
        else:
            # If no user account exists, create one
            username = emp_data.email.split('@')[0]
            result = await db.execute(select(User).filter(User.username == username))
            if not result.scalar_one_or_none():
                user = User(
                    username=username,
                    email=emp_data.email,
                    full_name=f"{emp_data.first_name} {emp_data.last_name}",
                    hashed_password=get_password_hash(emp_data.password),
                    user_type=UserType.EMPLOYEE,
                    is_active=True
                )
                db.add(user)
                await db.flush()
                employee.user_id = user.id
    
    employee.updated_at = datetime.utcnow()
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    
    return employee


@app.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: int,
    hard_delete: bool = False,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Employee).filter(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or employee.department_id != manager_dept:
            raise HTTPException(status_code=403, detail="Can only delete employees in your department")

    # Get associated user if exists
    user = None
    if employee.user_id:
        user_result = await db.execute(select(User).filter(User.id == employee.user_id))
        user = user_result.scalar_one_or_none()

    if hard_delete:
        # Permanent deletion from database - delete both employee and user
        if user:
            await db.delete(user)
        await db.delete(employee)
        await db.commit()
        return {"message": "Employee and associated user permanently deleted"}
    else:
        # Soft delete - mark both as inactive
        employee.is_active = False
        if user:
            user.is_active = False
        await db.commit()
        return {"message": "Employee deleted successfully"}


# Roles
@app.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    # Get manager's actual department assignment
    manager_dept = await get_manager_department(current_user, db)
    
    # Check if manager is trying to create role in a different department
    if current_user.user_type == UserType.MANAGER and role_data.department_id != manager_dept:
        raise HTTPException(status_code=403, detail="Can only create roles in your department")
    
    role = Role(**role_data.dict())
    db.add(role)
    await db.commit()
    await db.refresh(role)
    
    return role


@app.get("/roles", response_model=List[RoleDetailResponse])
async def list_roles(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List all roles with their shifts (eager loaded)"""
    stmt = select(Role).options(
        selectinload(Role.shifts),
        with_loader_criteria(Shift, Shift.is_active == True)
    )

    if current_user.user_type == UserType.ADMIN:
        stmt = stmt.filter(Role.is_active == True)
    else:
        # For managers, use get_manager_department helper
        manager_dept = await get_manager_department(current_user, db)
        stmt = stmt.filter(
            Role.department_id == manager_dept,
            Role.is_active == True
        )

    result = await db.execute(stmt)
    return result.scalars().unique().all()


@app.get("/roles/{role_id}", response_model=RoleDetailResponse)
async def get_role_detail(
    role_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get role with all shifts"""
    stmt = select(Role).options(
        selectinload(Role.shifts),
        with_loader_criteria(Shift, Shift.is_active == True)
    ).filter(Role.id == role_id, Role.is_active == True)

    if current_user.user_type != UserType.ADMIN:
        manager_dept = await get_manager_department(current_user, db)
        stmt = stmt.filter(Role.department_id == manager_dept)

    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@app.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Update a role"""
    result = await db.execute(
        select(Role).filter(Role.id == role_id)
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Get manager's actual department
    manager_dept = await get_manager_department(current_user, db)

    if role.department_id != manager_dept:
        raise HTTPException(status_code=403, detail="Can only update roles in your department")

    # Update only provided fields
    for key, value in role_data.dict(exclude_unset=True).items():
        if value is not None:
            setattr(role, key, value)

    await db.commit()
    await db.refresh(role)

    return role


@app.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Delete a role (soft delete by marking inactive)"""
    result = await db.execute(
        select(Role).filter(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Get manager's actual department
    manager_dept = await get_manager_department(current_user, db)
    
    if role.department_id != manager_dept:
        raise HTTPException(status_code=403, detail="Can only delete roles in your department")
    
    # Mark associated shifts as inactive so they disappear from role management views
    shift_result = await db.execute(
        select(Shift).filter(
            Shift.role_id == role_id,
            Shift.is_active == True
        )
    )
    role_shifts = shift_result.scalars().all()
    for shift in role_shifts:
        shift.is_active = False
    
    role.is_active = False
    await db.commit()
    
    return {"message": "Role and associated shifts deleted successfully"}

# Helper functions to resolve department ownership
async def get_user_department(user: User, db: AsyncSession) -> Optional[int]:
    """Resolve the department for a manager or employee user"""
    if user.user_type == UserType.MANAGER:
        result = await db.execute(select(Manager).filter(Manager.user_id == user.id))
        manager = result.scalar_one_or_none()
        return manager.department_id if manager else None
    
    if user.user_type == UserType.EMPLOYEE:
        result = await db.execute(select(Employee).filter(Employee.user_id == user.id))
        employee = result.scalar_one_or_none()
        return employee.department_id if employee else None
    
    return None


async def get_manager_department(user: User, db: AsyncSession) -> Optional[int]:
    """Get the department ID for a manager user"""
    if user.user_type != UserType.MANAGER:
        return None
    
    return await get_user_department(user, db)


# Employee: Check-In/Out
@app.post("/employee/check-in", response_model=CheckInResponse)
async def check_in(
    check_in_data: CheckInCreate,
    current_user: User = Depends(require_employee),
    db: AsyncSession = Depends(get_db)
):
    try:
        today = date.today()
        
        # Get employee by user_id
        result = await db.execute(
            select(Employee).filter(Employee.user_id == current_user.id)
        )
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=400, detail="Employee record not found")
        
        # Check if already checked in
        result = await db.execute(
            select(CheckInOut).filter(
                CheckInOut.employee_id == employee.id,
                CheckInOut.date == today,
                CheckInOut.check_out_time == None
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already checked in")
        
        # Get today's schedule
        result = await db.execute(
            select(Schedule).filter(
                Schedule.employee_id == employee.id,
                Schedule.date == today
            )
        )
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise HTTPException(status_code=400, detail="No scheduled shift for today")
        
        # Calculate late status
        now = datetime.now()
        try:
            if isinstance(schedule.start_time, str):
                scheduled_time = datetime.strptime(schedule.start_time, "%H:%M")
            else:
                scheduled_time = datetime.combine(datetime.today(), schedule.start_time)
            
            scheduled_datetime = datetime.combine(today, scheduled_time.time())
            diff_minutes = (now - scheduled_datetime).total_seconds() / 60
            
            if diff_minutes <= 0:
                status_val = "on-time"
            elif diff_minutes <= 15:
                status_val = "slightly-late"
            else:
                status_val = "late"
        except (ValueError, TypeError) as e:
            # If we can't parse the time, just mark as on-time
            status_val = "on-time"
        
        # Create check-in record
        check_in = CheckInOut(
            employee_id=employee.id,
            schedule_id=schedule.id,
            date=today,
            check_in_time=now,
            check_in_status=status_val,
            location=check_in_data.location
        )
        
        db.add(check_in)
        await db.commit()
        await db.refresh(check_in)
        
        return check_in
    except HTTPException:
        raise
    except Exception as e:
        print(f"Check-in error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Check-in failed: {str(e)}")


@app.post("/employee/check-out", response_model=CheckInResponse)
async def check_out(
    check_out_data: CheckOutCreate,
    current_user: User = Depends(require_employee),
    db: AsyncSession = Depends(get_db)
):
    try:
        today = date.today()
        
        # Get employee by user_id
        result = await db.execute(
            select(Employee).filter(Employee.user_id == current_user.id)
        )
        employee = result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=400, detail="Employee record not found")

        # Find today's check-in
        result = await db.execute(
            select(CheckInOut).options(
                selectinload(CheckInOut.employee).selectinload(Employee.user),
                selectinload(CheckInOut.schedule)
            ).filter(
                CheckInOut.employee_id == employee.id,
                CheckInOut.date == today,
                CheckInOut.check_out_time == None
            )
        )
        check_in = result.scalar_one_or_none()

        if not check_in:
            raise HTTPException(status_code=400, detail="No active check-in found")

        check_in.check_out_time = datetime.now()
        check_in.notes = check_out_data.notes

        await db.commit()
        await db.refresh(check_in, ['employee', 'schedule'])

        return check_in
    except HTTPException:
        raise
    except Exception as e:
        print(f"Check-out error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Check-out failed: {str(e)}")


# Attendance Management
@app.get("/attendance", response_model=List[CheckInResponse])
async def get_attendance(
    start_date: date = None,
    end_date: date = None,
    employee_id: int = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance records with optional filters"""
    query = select(CheckInOut).options(
        selectinload(CheckInOut.employee).selectinload(Employee.user),
        selectinload(CheckInOut.schedule)
    )

    # Role-based filtering
    if current_user.user_type == UserType.EMPLOYEE:
        # Get employee by user_id
        emp_result = await db.execute(
            select(Employee).filter(Employee.user_id == current_user.id)
        )
        employee = emp_result.scalar_one_or_none()
        if employee:
            query = query.filter(CheckInOut.employee_id == employee.id)
        else:
            return []
    elif current_user.user_type == UserType.MANAGER:
        # Get manager's actual department
        manager_dept = await get_manager_department(current_user, db)
        if manager_dept:
            subquery = select(Employee.id).filter(Employee.department_id == manager_dept)
            query = query.filter(CheckInOut.employee_id.in_(subquery))
        else:
            return []

    # Additional filters
    if employee_id and current_user.user_type != UserType.EMPLOYEE:
        query = query.filter(CheckInOut.employee_id == employee_id)

    if start_date:
        query = query.filter(CheckInOut.date >= start_date)
    if end_date:
        query = query.filter(CheckInOut.date <= end_date)

    result = await db.execute(query.order_by(CheckInOut.date.desc()))
    return result.scalars().all()


@app.get("/attendance/today")
async def get_todays_attendance(
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Get today's attendance summary for manager"""
    today = date.today()

    # Get all employees in department
    manager_dept = await get_manager_department(current_user, db)
    if not manager_dept:
        raise HTTPException(status_code=400, detail="Manager department not found")
    
    emp_result = await db.execute(
        select(Employee).filter(
            Employee.department_id == manager_dept,
            Employee.is_active == True
        )
    )
    employees = emp_result.scalars().all()

    # Get today's schedules
    sched_result = await db.execute(
        select(Schedule).filter(
            Schedule.department_id == manager_dept,
            Schedule.date == today
        )
    )
    schedules = sched_result.scalars().all()

    # Get today's check-ins
    checkin_result = await db.execute(
        select(CheckInOut).filter(
            CheckInOut.date == today
        )
    )
    checkins = {c.employee_id: c for c in checkin_result.scalars().all()}

    # Build attendance summary
    attendance_summary = []
    for schedule in schedules:
        checkin = checkins.get(schedule.employee_id)

        status = "absent"
        if checkin:
            if checkin.check_out_time:
                status = "completed"
            elif checkin.check_in_status == "on-time":
                status = "present"
            else:
                status = checkin.check_in_status

        attendance_summary.append({
            "employee_id": schedule.employee_id,
            "schedule_id": schedule.id,
            "scheduled_time": f"{schedule.start_time} - {schedule.end_time}",
            "check_in_time": checkin.check_in_time.isoformat() if checkin and checkin.check_in_time else None,
            "check_out_time": checkin.check_out_time.isoformat() if checkin and checkin.check_out_time else None,
            "status": status
        })

    return {
        "date": today.isoformat(),
        "total_scheduled": len(schedules),
        "total_checked_in": len(checkins),
        "attendance": attendance_summary
    }


@app.get("/attendance/stats")
async def get_attendance_stats(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance statistics"""
    query = select(CheckInOut).filter(
        CheckInOut.date >= start_date,
        CheckInOut.date <= end_date
    )

    if current_user.user_type == UserType.EMPLOYEE:
        query = query.filter(CheckInOut.employee_id == current_user.employee_id)
    elif current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if manager_dept:
            subquery = select(Employee.id).filter(Employee.department_id == manager_dept)
            query = query.filter(CheckInOut.employee_id.in_(subquery))
        else:
            query = query.filter(CheckInOut.employee_id == -1)  # Return empty

    result = await db.execute(query)
    records = result.scalars().all()

    total = len(records)
    on_time = len([r for r in records if r.check_in_status == "on-time"])
    late = len([r for r in records if r.check_in_status in ["slightly-late", "late"]])

    return {
        "total_days": total,
        "on_time": on_time,
        "late": late,
        "on_time_percentage": round((on_time / total * 100) if total > 0 else 0, 2)
    }


# Attendance Reports (Excel Export)
@app.get("/attendance/export/monthly")
async def export_monthly_attendance(
    department_id: int,
    year: int,
    month: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export monthly attendance report as Excel"""
    try:
        # Check authorization: only admins can download any department, managers only their own
        if current_user.user_type == UserType.MANAGER:
            # For managers, check if they manage this department
            manager_result = await db.execute(
                select(Manager).filter(Manager.user_id == current_user.id, Manager.department_id == department_id)
            )
            if not manager_result.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="You don't have permission to download reports for this department")
        elif current_user.user_type != UserType.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins and managers can download attendance reports")
        
        # Get department
        dept_result = await db.execute(select(Department).filter(Department.id == department_id))
        department = dept_result.scalar_one_or_none()
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # Get employees in department
        emp_result = await db.execute(
            select(Employee).filter(Employee.department_id == department_id, Employee.is_active == True)
        )
        employees = emp_result.scalars().all()
        
        # Get attendance for the month
        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])
        
        att_result = await db.execute(
            select(CheckInOut).filter(
                CheckInOut.employee_id.in_([e.id for e in employees]) if employees else False,
                CheckInOut.date >= start_date,
                CheckInOut.date <= end_date
            ).order_by(CheckInOut.date, CheckInOut.employee_id)
        )
        attendance_records = att_result.scalars().all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"Attendance"
        
        # Header styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Title
        ws['A1'] = f"{department.name} - Monthly Attendance Report"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:F1')
        
        ws['A2'] = f"December 2025"  # Simplified to avoid datetime issues
        ws.merge_cells('A2:F2')
        
        # Headers
        headers = ['Employee ID', 'Name', 'Date', 'Check-In', 'Check-Out', 'Status']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border
        
        # Data
        row = 5
        for record in attendance_records:
            employee = next((e for e in employees if e.id == record.employee_id), None)
            if employee:
                ws.cell(row=row, column=1).value = employee.employee_id
                ws.cell(row=row, column=2).value = f"{employee.first_name} {employee.last_name}"
                ws.cell(row=row, column=3).value = record.date.isoformat()
                ws.cell(row=row, column=4).value = record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else '-'
                ws.cell(row=row, column=5).value = record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else '-'
                ws.cell(row=row, column=6).value = record.check_in_status or '-'
                
                for col in range(1, 7):
                    ws.cell(row=row, column=col).border = border
                row += 1
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 12
        
        # Save to bytes
        file_bytes = io.BytesIO()
        wb.save(file_bytes)
        file_bytes.seek(0)
        
        return StreamingResponse(
            iter([file_bytes.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={department.name}_attendance_{year}-{month:02d}.xlsx"}
        )
    except Exception as e:
        print(f"Export error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/attendance/export/weekly")
async def export_weekly_attendance(
    department_id: int,
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Export weekly attendance report as Excel"""
    try:
        # Check authorization: only admins can download any department, managers only their own
        if current_user.user_type == UserType.MANAGER:
            # For managers, check if they manage this department
            manager_result = await db.execute(
                select(Manager).filter(Manager.user_id == current_user.id, Manager.department_id == department_id)
            )
            if not manager_result.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="You don't have permission to download reports for this department")
        elif current_user.user_type != UserType.ADMIN:
            raise HTTPException(status_code=403, detail="Only admins and managers can download attendance reports")
        
        # Get department
        dept_result = await db.execute(select(Department).filter(Department.id == department_id))
        department = dept_result.scalar_one_or_none()
        if not department:
            raise HTTPException(status_code=404, detail="Department not found")
        
        # Get employees in department
        emp_result = await db.execute(
            select(Employee).filter(Employee.department_id == department_id, Employee.is_active == True)
        )
        employees = emp_result.scalars().all()
        
        # Get attendance for the week
        att_result = await db.execute(
            select(CheckInOut).filter(
                CheckInOut.employee_id.in_([e.id for e in employees]) if employees else False,
                CheckInOut.date >= start_date,
                CheckInOut.date <= end_date
            ).order_by(CheckInOut.date, CheckInOut.employee_id)
        )
        attendance_records = att_result.scalars().all()
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Weekly"
        
        # Header styles
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Title
        ws['A1'] = f"{department.name} - Weekly Attendance Report"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:F1')
        
        ws['A2'] = f"{start_date.isoformat()} to {end_date.isoformat()}"
        ws.merge_cells('A2:F2')
        
        # Headers
        headers = ['Employee ID', 'Name', 'Date', 'Check-In', 'Check-Out', 'Status']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = border
        
        # Data
        row = 5
        for record in attendance_records:
            employee = next((e for e in employees if e.id == record.employee_id), None)
            if employee:
                ws.cell(row=row, column=1).value = employee.employee_id
                ws.cell(row=row, column=2).value = f"{employee.first_name} {employee.last_name}"
                ws.cell(row=row, column=3).value = record.date.isoformat()
                ws.cell(row=row, column=4).value = record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else '-'
                ws.cell(row=row, column=5).value = record.check_out_time.strftime('%H:%M:%S') if record.check_out_time else '-'
                ws.cell(row=row, column=6).value = record.check_in_status or '-'
                
                for col in range(1, 7):
                    ws.cell(row=row, column=col).border = border
                row += 1
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 12
        ws.column_dimensions['F'].width = 12
        
        # Save to bytes
        file_bytes = io.BytesIO()
        wb.save(file_bytes)
        file_bytes.seek(0)
        
        return StreamingResponse(
            iter([file_bytes.getvalue()]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={department.name}_attendance_{start_date.isoformat()}_to_{end_date.isoformat()}.xlsx"}
        )
    except Exception as e:
        print(f"Weekly export error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    
    # Save to bytes
    file_bytes = io.BytesIO()
    wb.save(file_bytes)
    file_bytes.seek(0)
    
    return StreamingResponse(
        iter([file_bytes.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={department.name}_attendance_{start_date.isoformat()}_to_{end_date.isoformat()}.xlsx"}
    )


# Leave Requests
@app.post("/leave-requests", response_model=LeaveRequestResponse)
async def create_leave_request(
    leave_data: LeaveRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Validate that required fields are provided
    if not leave_data.start_date:
        raise HTTPException(status_code=400, detail="Leave request must have a start date")
    if not leave_data.end_date:
        raise HTTPException(status_code=400, detail="Leave request must have an end date")
    if not leave_data.leave_type:
        raise HTTPException(status_code=400, detail="Leave request must have a leave type")
    
    # Validate date range
    if leave_data.end_date < leave_data.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")
    
    # Employee can only request for themselves
    if current_user.user_type == UserType.EMPLOYEE:
        # Find employee record linked to this user
        result = await db.execute(select(Employee).filter(Employee.user_id == current_user.id))
        employee = result.scalar_one_or_none()
        if not employee or leave_data.employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Can only request leave for yourself")
    
    leave_request = LeaveRequest(**leave_data.dict())
    db.add(leave_request)
    await db.commit()
    await db.refresh(leave_request)
    
    return leave_request


@app.get("/leave-requests", response_model=List[LeaveRequestResponse])
async def list_leave_requests(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.user_type == UserType.EMPLOYEE:
        # Get employee record for current user
        emp_result = await db.execute(
            select(Employee).filter(Employee.user_id == current_user.id)
        )
        employee = emp_result.scalar_one_or_none()
        if not employee:
            return []
        
        result = await db.execute(
            select(LeaveRequest).filter(LeaveRequest.employee_id == employee.id)
        )
    elif current_user.user_type == UserType.MANAGER:
        # Get all leave requests for employees in manager's department
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept:
            return []
        
        result = await db.execute(
            select(LeaveRequest)
            .join(Employee)
            .filter(Employee.department_id == manager_dept)
        )
    else:  # Admin
        result = await db.execute(select(LeaveRequest))
    
    return result.scalars().all()


@app.post("/manager/approve-leave/{leave_id}")
async def approve_leave(
    leave_id: int,
    approval_data: LeaveApproval,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeaveRequest).filter(LeaveRequest.id == leave_id))
    leave_request = result.scalar_one_or_none()

    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # Get the manager record for current user
    manager_result = await db.execute(select(Manager).filter(Manager.user_id == current_user.id))
    manager = manager_result.scalar_one_or_none()

    if not manager:
        raise HTTPException(status_code=403, detail="User is not a manager")

    leave_request.status = LeaveStatus.APPROVED
    leave_request.manager_id = manager.id
    leave_request.reviewed_at = datetime.utcnow()
    leave_request.review_notes = approval_data.review_notes

    await db.commit()

    return {"message": "Leave approved successfully"}


@app.post("/manager/reject-leave/{leave_id}")
async def reject_leave(
    leave_id: int,
    approval_data: LeaveApproval,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LeaveRequest).filter(LeaveRequest.id == leave_id))
    leave_request = result.scalar_one_or_none()

    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")

    # Get the manager record for current user
    manager_result = await db.execute(select(Manager).filter(Manager.user_id == current_user.id))
    manager = manager_result.scalar_one_or_none()

    if not manager:
        raise HTTPException(status_code=403, detail="User is not a manager")

    leave_request.status = LeaveStatus.REJECTED
    leave_request.manager_id = manager.id
    leave_request.reviewed_at = datetime.utcnow()
    leave_request.review_notes = approval_data.review_notes

    await db.commit()

    return {"message": "Leave rejected"}


# Messages
@app.post("/messages", response_model=MessageResponse)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    message = Message(
        sender_id=current_user.id,
        recipient_id=message_data.recipient_id,
        department_id=message_data.department_id,
        subject=message_data.subject,
        message=message_data.message
    )
    
    db.add(message)
    await db.commit()
    
    # Refresh and eagerly load relationships
    await db.refresh(message, ['sender', 'recipient'])
    
    return message


@app.get("/messages", response_model=List[MessageResponse])
async def get_messages(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Get messages: either sent by user, sent to user, or sent to their department
    user_department_id = await get_user_department(current_user, db)
    department_filters = []
    if user_department_id is not None:
        department_filters.append(
            and_(
                Message.department_id == user_department_id,
                Message.is_deleted_by_recipient == False
            )
        )
    
    result = await db.execute(
        select(Message).options(
            selectinload(Message.sender),
            selectinload(Message.recipient)
        ).filter(
            or_(
                and_(
                    Message.sender_id == current_user.id,  # Messages sent by the user
                    Message.is_deleted_by_sender == False
                ),
                and_(
                    Message.recipient_id == current_user.id,
                    Message.is_deleted_by_recipient == False
                ),
                *department_filters
            )
        ).order_by(Message.created_at.desc())
    )
    
    return result.scalars().all()


@app.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Message).filter(Message.id == message_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Soft delete based on user role
    if message.sender_id == current_user.id:
        message.is_deleted_by_sender = True
    elif message.recipient_id == current_user.id:
        message.is_deleted_by_recipient = True
    else:
        raise HTTPException(status_code=403, detail="Cannot delete this message")
    
    await db.commit()

    return {"message": "Message deleted"}


@app.put("/messages/{message_id}/read")
async def mark_message_as_read(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Message).filter(Message.id == message_id))
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Only the recipient or department can mark as read
    user_department_id = await get_user_department(current_user, db)
    if message.recipient_id != current_user.id and message.department_id != user_department_id:
        raise HTTPException(status_code=403, detail="Cannot mark this message as read")
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Message marked as read"}


# Notifications
@app.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Notification).filter(Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    result = await db.execute(query.order_by(Notification.created_at.desc()))
    return result.scalars().all()


@app.post("/notifications/{notification_id}/mark-read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()

    return {"message": "Notification marked as read"}


@app.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    notifications = result.scalars().all()

    for notification in notifications:
        notification.is_read = True

    await db.commit()

    return {"message": f"{len(notifications)} notifications marked as read"}


@app.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()

    return {"message": "Notification deleted"}


# Schedules
@app.get("/schedules", response_model=List[ScheduleResponse])
async def get_schedules(
    start_date: date = None,
    end_date: date = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Schedule).options(
        selectinload(Schedule.employee).selectinload(Employee.user),
        selectinload(Schedule.role)
    )

    if current_user.user_type == UserType.EMPLOYEE:
        # Get employee by user_id
        emp_result = await db.execute(
            select(Employee).filter(Employee.user_id == current_user.id)
        )
        employee = emp_result.scalar_one_or_none()
        if employee:
            query = query.filter(Schedule.employee_id == employee.id)
        else:
            return []
    elif current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if manager_dept:
            query = query.filter(Schedule.department_id == manager_dept)
        else:
            return []

    if start_date:
        query = query.filter(Schedule.date >= start_date)
    if end_date:
        query = query.filter(Schedule.date <= end_date)

    result = await db.execute(query.order_by(Schedule.date))
    return result.scalars().all()


@app.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    # Get employee to verify department
    result = await db.execute(select(Employee).filter(Employee.id == schedule_data.employee_id))
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or employee.department_id != manager_dept:
            raise HTTPException(status_code=403, detail="Can only schedule employees in your department")

    schedule = Schedule(
        department_id=employee.department_id,
        employee_id=schedule_data.employee_id,
        role_id=schedule_data.role_id,
        shift_id=schedule_data.shift_id,  # Optional - can be None for custom schedules
        date=schedule_data.date,
        start_time=schedule_data.start_time,
        end_time=schedule_data.end_time,
        notes=schedule_data.notes,
        status='scheduled'
    )

    db.add(schedule)
    await db.commit()

    # Refresh with eager loading
    result = await db.execute(
        select(Schedule)
        .filter(Schedule.id == schedule.id)
        .options(selectinload(Schedule.role))
    )
    return result.scalar_one()


@app.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Schedule).filter(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or schedule.department_id != manager_dept:
            raise HTTPException(status_code=403, detail="Can only edit schedules in your department")

    for key, value in schedule_data.dict(exclude_unset=True).items():
        # Convert string date to date object if needed
        if key == 'date' and isinstance(value, str):
            value = datetime.strptime(value, '%Y-%m-%d').date()
        setattr(schedule, key, value)

    schedule.updated_at = datetime.utcnow()
    await db.commit()

    # Re-fetch with eager loading
    result = await db.execute(
        select(Schedule)
        .filter(Schedule.id == schedule_id)
        .options(selectinload(Schedule.role))
    )
    return result.scalar_one()


@app.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Schedule).filter(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or schedule.department_id != manager_dept:
            raise HTTPException(status_code=403, detail="Can only delete schedules in your department")

    await db.delete(schedule)
    await db.commit()

    return {"message": "Schedule deleted successfully"}


@app.post("/schedules/generate")
async def generate_schedules(
    start_date: date,
    end_date: date,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate fair schedules with equal shift distribution.

    Algorithm:
    1. Get all roles and shifts for the department in the date range
    2. Get all employees in the department
    3. Calculate each employee's capacity (shifts per week)
    4. Fairly assign shifts equally across different shift types
    5. Respect min_emp and max_emp constraints for each shift
    """
    try:
        print(f"[DEBUG] Schedule generation started for dates {start_date} to {end_date}", flush=True)

        # Get manager's department
        department_id = await get_manager_department(current_user, db)
        if not department_id:
            raise HTTPException(status_code=400, detail="Manager department not found")

        print(f"[DEBUG] Department ID: {department_id}", flush=True)

        # Get all roles in this department
        roles_result = await db.execute(
            select(Role)
            .filter(Role.department_id == department_id, Role.is_active == True)
        )
        roles = roles_result.scalars().all()
        print(f"[DEBUG] Found {len(roles)} roles", flush=True)

        if not roles:
            return {
                "success": True,
                "schedules_created": 0,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "feedback": ["❌ No active roles found in your department. Create roles first."],
                "schedules": []
            }

        # Get all shifts for these roles
        role_ids = [r.id for r in roles]
        shifts_result = await db.execute(
            select(Shift)
            .filter(Shift.role_id.in_(role_ids), Shift.is_active == True)
        )
        shifts = shifts_result.scalars().all()
        print(f"[DEBUG] Found {len(shifts)} shifts", flush=True)

        # Log shift details
        for shift in shifts:
            print(f"[DEBUG] Shift: {shift.id} - {shift.name}, active={shift.is_active}, time={shift.start_time}-{shift.end_time}, min_emp={shift.min_emp}, role_id={shift.role_id}", flush=True)

        if not shifts:
            return {
                "success": True,
                "schedules_created": 0,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "feedback": ["❌ No active shifts found in your roles. Create shifts first."],
                "schedules": []
            }

        # Get all employees in the department
        employees_result = await db.execute(
            select(Employee)
            .filter(Employee.department_id == department_id, Employee.is_active == True)
        )
        employees = employees_result.scalars().all()
        print(f"[DEBUG] Found {len(employees)} employees", flush=True)

        # Log employee details
        for emp in employees:
            print(f"[DEBUG] Employee: {emp.id} - {emp.first_name}, active={emp.is_active}, weekly_hours={emp.weekly_hours}, daily_max={emp.daily_max_hours}, shifts_per_week={emp.shifts_per_week}", flush=True)

        if not employees:
            return {
                "success": True,
                "schedules_created": 0,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "feedback": ["❌ No active employees found in your department. Create employees first."],
                "schedules": []
            }

        # Generate date range (one schedule per shift per day)
        current_date = start_date
        schedules_created = 0
        feedback = []

        # Group shifts by role for fair distribution
        shifts_by_role = defaultdict(list)
        for shift in shifts:
            shifts_by_role[shift.role_id].append(shift)

        # Calculate employee capacity and pre-assign shifts
        shift_assignments = defaultdict(lambda: defaultdict(int))  # {shift_id: {emp_id: count}}

        # For each shift, distribute based on employee capacity
        for shift in shifts:
            # Distribute this shift across employees based on capacity
            for emp in employees:
                # Only assign employees who are either:
                # 1. Not assigned to any specific role (flexible), OR
                # 2. Assigned to this shift's role
                if emp.role_id is not None and emp.role_id != shift.role_id:
                    continue  # Skip employees not assigned to this role

                # Calculate employee capacity for this week
                weekly_hours = emp.weekly_hours or 40
                daily_max = emp.daily_max_hours or 8
                shifts_per_week = emp.shifts_per_week or 5

                # Max shifts this employee can work per week (most limiting factor)
                max_capacity = min(shifts_per_week, int(weekly_hours / daily_max))

                # Simply assign the full capacity for each shift they're eligible for
                # The actual schedule creation loop will handle the distribution
                shift_assignments[shift.id][emp.id] = max_capacity
                print(f"[DEBUG] Assigned {emp.id} ({emp.first_name}) to shift {shift.id} with capacity {max_capacity}", flush=True)

        # Create schedules
        current_date = start_date
        while current_date <= end_date:
            day_name = current_date.strftime('%A').lower()

            for shift in shifts:
                # Check if shift operates on this day
                role = next((r for r in roles if r.id == shift.role_id), None)
                print(f"[DEBUG] Processing shift {shift.id} on {current_date} ({day_name}), role schedule_config: {role.schedule_config if role else 'N/A'}", flush=True)

                # Check if role has schedule_config - if yes, only process enabled days
                # If no schedule_config, assume all days are enabled
                should_skip = False
                if role and role.schedule_config and isinstance(role.schedule_config, dict) and len(role.schedule_config) > 0:
                    # Role has a schedule_config, so only process days that are explicitly enabled
                    if not role.schedule_config.get(day_name, False):
                        should_skip = True
                        print(f"[DEBUG] ✗ Day {day_name} is disabled for role {role.id}, skipping", flush=True)

                if should_skip:
                    continue
                else:
                    print(f"[DEBUG] ✓ Processing day {day_name} for role {role.id if role else 'N/A'}", flush=True)

                # Assign employees to this shift on this day
                assigned_count = 0
                for emp in employees:
                    if (shift.id in shift_assignments and
                        emp.id in shift_assignments[shift.id] and
                        shift_assignments[shift.id][emp.id] > 0):
                        print(f"[DEBUG] Checking {emp.first_name} for shift {shift.id} on {current_date}, remaining: {shift_assignments[shift.id][emp.id]}", flush=True)

                        # Check if employee has leave or is unavailable
                        leave_result = await db.execute(
                            select(LeaveRequest)
                            .filter(
                                LeaveRequest.employee_id == emp.id,
                                LeaveRequest.start_date <= current_date,
                                LeaveRequest.end_date >= current_date,
                                LeaveRequest.status == LeaveStatus.APPROVED
                            )
                        )
                        if leave_result.scalar_one_or_none():
                            continue  # Skip if employee is on leave

                        # Check if employee exceeded weekly hours limit
                        week_start = current_date - timedelta(days=current_date.weekday())
                        week_end = week_start + timedelta(days=6)

                        # Fetch existing schedules for the week (with eager loading of role)
                        existing_schedules_result = await db.execute(
                            select(Schedule)
                            .filter(
                                Schedule.employee_id == emp.id,
                                Schedule.date >= week_start,
                                Schedule.date <= week_end
                            )
                            .options(selectinload(Schedule.role))
                        )
                        existing_schedules = existing_schedules_result.scalars().all()

                        # Calculate existing hours in Python, subtracting break time
                        existing_hours = 0
                        existing_hours_today = 0
                        for sched in existing_schedules:
                            if sched.start_time and sched.end_time:
                                try:
                                    start = datetime.strptime(sched.start_time, '%H:%M')
                                    end = datetime.strptime(sched.end_time, '%H:%M')
                                    total_hours = (end - start).total_seconds() / 3600

                                    # Subtract break time from role
                                    break_hours = (sched.role.break_minutes or 0) / 60 if sched.role else 0
                                    work_hours = total_hours - break_hours

                                    existing_hours += work_hours
                                    # Check hours for current day
                                    if sched.date == current_date:
                                        existing_hours_today += work_hours
                                except (ValueError, TypeError):
                                    pass

                        # Calculate shift hours (total time) and work hours (minus breaks)
                        shift_start = datetime.strptime(shift.start_time, '%H:%M')
                        shift_end = datetime.strptime(shift.end_time, '%H:%M')
                        total_shift_hours = (shift_end - shift_start).total_seconds() / 3600

                        # Subtract break time from role
                        break_hours = (role.break_minutes or 0) / 60
                        work_hours = total_shift_hours - break_hours

                        # Check both weekly and daily limits using work hours (excluding breaks)
                        daily_max = emp.daily_max_hours or 8
                        print(f"[DEBUG] Hours check: existing_weekly={existing_hours:.1f} + work={work_hours:.1f} <= {emp.weekly_hours} AND existing_daily={existing_hours_today:.1f} + work={work_hours:.1f} <= {daily_max}", flush=True)

                        if (existing_hours + work_hours <= emp.weekly_hours and
                            existing_hours_today + work_hours <= daily_max):
                            print(f"[DEBUG] ✓ Creating schedule for {emp.first_name} on {current_date}", flush=True)
                            # Create schedule
                            schedule = Schedule(
                                department_id=department_id,
                                employee_id=emp.id,
                                role_id=shift.role_id,
                                shift_id=shift.id,
                                date=current_date,
                                start_time=shift.start_time,
                                end_time=shift.end_time,
                                status="scheduled"
                            )
                            db.add(schedule)
                            schedules_created += 1
                            assigned_count += 1
                            shift_assignments[shift.id][emp.id] -= 1

                            if assigned_count >= shift.max_emp:
                                break  # Max employees for this shift on this day

                # Ensure minimum employees are assigned
                if assigned_count < shift.min_emp:
                    feedback.append(f"Warning: {shift.name} on {current_date} has {assigned_count} employees (min: {shift.min_emp})")

            current_date += timedelta(days=1)

        await db.commit()

        feedback.insert(0, f"Successfully generated {schedules_created} schedules")

        return {
            "success": True,
            "schedules_created": schedules_created,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "feedback": feedback,
            "schedules": []
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in schedule generation: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Schedule generation error: {str(e)}")


@app.get("/schedules/conflicts")
async def check_schedule_conflicts(
    start_date: date,
    end_date: date,
    current_user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db)
):
    """Check for scheduling conflicts"""
    manager_dept = await get_manager_department(current_user, db)
    if not manager_dept:
        raise HTTPException(status_code=400, detail="Manager department not found")
    
    result = await db.execute(
        select(Schedule).filter(
            Schedule.department_id == manager_dept,
            Schedule.date >= start_date,
            Schedule.date <= end_date
        )
    )
    schedules = result.scalars().all()

    # Group by employee and date
    employee_schedules = defaultdict(lambda: defaultdict(list))
    for schedule in schedules:
        employee_schedules[schedule.employee_id][schedule.date].append(schedule)

    conflicts = []
    for emp_id, dates in employee_schedules.items():
        for date, scheds in dates.items():
            if len(scheds) > 1:
                conflicts.append({
                    "employee_id": emp_id,
                    "date": date.isoformat(),
                    "conflicting_schedules": [
                        {
                            "id": s.id,
                            "role_id": s.role_id,
                            "time": f"{s.start_time} - {s.end_time}"
                        }
                        for s in scheds
                    ]
                })

    return {
        "conflicts_found": len(conflicts),
        "conflicts": conflicts
    }


# ==================== ATTENDANCE MANAGEMENT ====================

@app.post("/attendance/record", response_model=AttendanceResponse)
async def record_attendance(
    attendance_data: AttendanceCreate,
    current_user: User = Depends(require_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Record attendance with check-in time
    Calculates status based on scheduled time
    """
    from datetime import datetime as dt
    
    today = date.today()
    
    # Check if already checked in
    result = await db.execute(
        select(Attendance).filter(
            Attendance.employee_id == current_user.employee_id,
            Attendance.date == today,
            Attendance.in_time.isnot(None)
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already checked in today")
    
    # Get schedule for today
    if attendance_data.schedule_id:
        result = await db.execute(
            select(Schedule).filter(
                Schedule.id == attendance_data.schedule_id,
                Schedule.employee_id == current_user.employee_id,
                Schedule.date == today
            )
        )
    else:
        result = await db.execute(
            select(Schedule).filter(
                Schedule.employee_id == current_user.employee_id,
                Schedule.date == today
            )
        )
    
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=400, detail="No scheduled shift for today")
    
    # Calculate status based on check-in time
    try:
        in_time_parts = attendance_data.in_time.split(':')
        in_hour, in_min = int(in_time_parts[0]), int(in_time_parts[1])
        in_minutes = in_hour * 60 + in_min
        
        start_time_parts = schedule.start_time.split(':')
        start_hour, start_min = int(start_time_parts[0]), int(start_time_parts[1])
        start_minutes = start_hour * 60 + start_min
        
        diff_minutes = in_minutes - start_minutes
        
        if diff_minutes <= 0:
            status_val = "onTime"
        elif diff_minutes <= 15:
            status_val = "slightlyLate"
        elif diff_minutes <= 60:
            status_val = "late"
        else:
            status_val = "veryLate"
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid time format")
    
    # Create attendance record
    attendance = Attendance(
        employee_id=current_user.employee_id,
        schedule_id=attendance_data.schedule_id,
        date=today,
        in_time=attendance_data.in_time,
        status=status_val,
        notes=attendance_data.notes
    )
    
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)
    
    return attendance


@app.put("/attendance/{attendance_id}/checkout")
async def record_checkout(
    attendance_id: int,
    checkout_data: AttendanceUpdate,
    current_user: User = Depends(require_employee),
    db: AsyncSession = Depends(get_db)
):
    """
    Record check-out time and calculate worked hours
    """
    result = await db.execute(
        select(Attendance).filter(
            Attendance.id == attendance_id,
            Attendance.employee_id == current_user.employee_id
        )
    )
    attendance = result.scalar_one_or_none()
    
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    if not checkout_data.out_time:
        raise HTTPException(status_code=400, detail="Out time is required")
    
    # Calculate worked hours
    if attendance.in_time and checkout_data.out_time:
        try:
            in_parts = attendance.in_time.split(':')
            out_parts = checkout_data.out_time.split(':')
            
            in_minutes = int(in_parts[0]) * 60 + int(in_parts[1])
            out_minutes = int(out_parts[0]) * 60 + int(out_parts[1])
            
            if out_minutes < in_minutes:
                out_minutes += 24 * 60  # Handle overnight shifts
            
            total_minutes = out_minutes - in_minutes
            
            # Get role for break time
            schedule = await db.get(Schedule, attendance.schedule_id)
            if schedule:
                role = await db.get(Role, schedule.role_id)
                break_minutes = role.break_minutes if role else 0
            else:
                break_minutes = 0
            
            # Calculate worked hours
            worked_minutes = total_minutes - break_minutes
            worked_hours = max(0, worked_minutes / 60)
            
            attendance.worked_hours = round(worked_hours, 2)
            attendance.break_minutes = break_minutes
            
            # Calculate overtime if exceeds daily max
            if schedule:
                emp = await db.get(Employee, attendance.employee_id)
                if emp and worked_hours > emp.daily_max_hours:
                    attendance.overtime_hours = round(worked_hours - emp.daily_max_hours, 2)
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid time format")
    
    attendance.out_time = checkout_data.out_time
    attendance.out_status = checkout_data.out_status
    attendance.notes = checkout_data.notes or attendance.notes
    
    await db.commit()
    await db.refresh(attendance)
    
    return attendance


@app.get("/attendance/weekly/{employee_id}")
async def get_weekly_attendance(
    employee_id: int,
    start_date: date,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get weekly attendance for an employee"""
    # Check authorization
    if current_user.user_type == UserType.EMPLOYEE and current_user.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Cannot view other employees' attendance")
    
    # Calculate week end
    end_date = start_date + timedelta(days=6)
    
    # Get attendance records
    result = await db.execute(
        select(Attendance).filter(
            Attendance.employee_id == employee_id,
            Attendance.date >= start_date,
            Attendance.date <= end_date
        ).order_by(Attendance.date)
    )
    records = result.scalars().all()
    
    # Calculate weekly stats
    total_worked = sum(r.worked_hours for r in records)
    total_overtime = sum(r.overtime_hours for r in records)
    on_time_count = len([r for r in records if r.status == "onTime"])
    late_count = len([r for r in records if r.status in ["slightlyLate", "late", "veryLate"]])
    
    return {
        "employee_id": employee_id,
        "week_start": start_date.isoformat(),
        "week_end": end_date.isoformat(),
        "records": [
            {
                "date": r.date.isoformat(),
                "in_time": r.in_time,
                "out_time": r.out_time,
                "status": r.status,
                "worked_hours": r.worked_hours,
                "overtime_hours": r.overtime_hours
            }
            for r in records
        ],
        "summary": {
            "total_days_worked": len(records),
            "total_worked_hours": round(total_worked, 2),
            "total_overtime_hours": round(total_overtime, 2),
            "on_time_count": on_time_count,
            "late_count": late_count,
            "on_time_percentage": round((on_time_count / len(records) * 100) if records else 0, 2)
        }
    }


@app.get("/attendance/summary")
async def get_attendance_summary(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get attendance summary for department or individual"""
    query = select(Attendance).filter(
        Attendance.date >= start_date,
        Attendance.date <= end_date
    )
    
    if current_user.user_type == UserType.EMPLOYEE:
        query = query.filter(Attendance.employee_id == current_user.employee_id)
    elif current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept:
            return []
        # Get employees in manager's department
        subquery = select(Employee.id).filter(
            Employee.department_id == manager_dept
        )
        query = query.filter(Attendance.employee_id.in_(subquery))
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    # Group by employee
    emp_stats = defaultdict(lambda: {
        "total_worked_hours": 0,
        "total_overtime": 0,
        "on_time": 0,
        "late": 0,
        "total_days": 0
    })
    
    for record in records:
        stats = emp_stats[record.employee_id]
        stats["total_worked_hours"] += record.worked_hours
        stats["total_overtime"] += record.overtime_hours
        if record.status == "onTime":
            stats["on_time"] += 1
        elif record.status in ["slightlyLate", "late", "veryLate"]:
            stats["late"] += 1
        stats["total_days"] += 1
    
    # Convert to list with employee details
    summary_list = []
    for emp_id, stats in emp_stats.items():
        emp = await db.get(Employee, emp_id)
        if emp:
            summary_list.append({
                "employee_id": emp_id,
                "employee_name": f"{emp.first_name} {emp.last_name}",
                "total_worked_hours": round(stats["total_worked_hours"], 2),
                "total_overtime": round(stats["total_overtime"], 2),
                "on_time_percentage": round((stats["on_time"] / stats["total_days"] * 100) if stats["total_days"] > 0 else 0, 2),
                "late_count": stats["late"],
                "days_worked": stats["total_days"]
            })
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "summary": sorted(summary_list, key=lambda x: x["total_worked_hours"], reverse=True)
    }


# ===== UNAVAILABILITY MANAGEMENT =====

@app.post("/unavailability", response_model=UnavailabilityResponse)
async def create_unavailability(
    unavail: UnavailabilityCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark an employee as unavailable for a specific date (manager only)"""
    if current_user.user_type not in [UserType.ADMIN, UserType.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check employee belongs to manager's department
    result = await db.execute(select(Employee).filter(Employee.id == unavail.employee_id))
    employee = result.scalar_one_or_none()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or employee.department_id != manager_dept:
            raise HTTPException(status_code=404, detail="Employee not found")
    
    from app.models import Unavailability
    unavailability = Unavailability(
        employee_id=unavail.employee_id,
        date=unavail.date,
        reason=unavail.reason
    )
    db.add(unavailability)
    await db.commit()
    await db.refresh(unavailability)
    return unavailability


@app.get("/unavailability", response_model=List[UnavailabilityResponse])
async def list_unavailability(
    employee_id: int = None,
    start_date: date = None,
    end_date: date = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List unavailability records for department (manager) or specific employee (employee)"""
    from app.models import Unavailability
    
    query = select(Unavailability)
    
    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept:
            raise HTTPException(status_code=403, detail="Not authorized")
        # Manager sees unavailability for employees in their department
        if employee_id:
            result = await db.execute(select(Employee).filter(Employee.id == employee_id))
            employee = result.scalar_one_or_none()
            if not employee or employee.department_id != manager_dept:
                raise HTTPException(status_code=404, detail="Employee not found")
            query = query.filter(Unavailability.employee_id == employee_id)
    elif current_user.user_type == UserType.EMPLOYEE:
        # Employee sees only their own unavailability
        result = await db.execute(select(Employee).filter(Employee.user_id == current_user.id))
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee record not found")
        query = query.filter(Unavailability.employee_id == employee.id)
    
    if start_date:
        query = query.filter(Unavailability.date >= start_date)
    if end_date:
        query = query.filter(Unavailability.date <= end_date)
    
    result = await db.execute(query.order_by(Unavailability.date))
    unavailability_list = result.scalars().all()
    return unavailability_list


@app.delete("/unavailability/{unavailability_id}")
async def delete_unavailability(
    unavailability_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete an unavailability record (manager only)"""
    if current_user.user_type not in [UserType.ADMIN, UserType.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from app.models import Unavailability
    result = await db.execute(select(Unavailability).filter(Unavailability.id == unavailability_id))
    unavailability = result.scalar_one_or_none()
    
    if not unavailability:
        raise HTTPException(status_code=404, detail="Unavailability record not found")
    
    # Verify employee belongs to manager's department
    result = await db.execute(select(Employee).filter(Employee.id == unavailability.employee_id))
    employee = result.scalar_one_or_none()
    
    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or employee.department_id != manager_dept:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.delete(unavailability)
    await db.commit()
    
    return {"detail": "Unavailability record deleted successfully"}


# ===== SHIFT MANAGEMENT =====

@app.post("/shifts", response_model=ShiftResponse)
async def create_shift(
    shift: ShiftCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new shift type for a role (manager only)"""
    if current_user.user_type not in [UserType.ADMIN, UserType.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Verify role belongs to manager's department
    result = await db.execute(select(Role).filter(Role.id == shift.role_id))
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or role.department_id != manager_dept:
            raise HTTPException(status_code=404, detail="Role not found")
    
    from app.models import Shift
    new_shift = Shift(
        role_id=shift.role_id,
        name=shift.name,
        start_time=shift.start_time,
        end_time=shift.end_time,
        priority=shift.priority,
        min_emp=shift.min_emp,
        max_emp=shift.max_emp,
        schedule_config=shift.schedule_config
    )
    db.add(new_shift)
    await db.commit()
    await db.refresh(new_shift)
    return new_shift


@app.get("/shifts", response_model=List[ShiftResponse])
async def list_shifts(
    role_id: int = None,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List shifts for a role or department (manager)"""
    query = select(Shift)

    if role_id:
        query = query.filter(Shift.role_id == role_id)

    if not include_inactive:
        query = query.filter(Shift.is_active == True)

    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept:
            raise HTTPException(status_code=403, detail="Not authorized")
        query = query.join(Role).filter(Role.department_id == manager_dept)
    elif current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(query.order_by(Shift.created_at.desc()))
    shifts = result.scalars().all()
    return shifts


@app.put("/shifts/{shift_id}", response_model=ShiftResponse)
async def update_shift(
    shift_id: int,
    shift_update: ShiftUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a shift (manager only)"""
    if current_user.user_type not in [UserType.ADMIN, UserType.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")

    from app.models import Shift
    result = await db.execute(select(Shift).filter(Shift.id == shift_id))
    shift = result.scalar_one_or_none()

    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Verify shift's role belongs to manager's department
    result = await db.execute(select(Role).filter(Role.id == shift.role_id))
    role = result.scalar_one_or_none()

    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or role.department_id != manager_dept:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Update only provided fields
    for key, value in shift_update.dict(exclude_unset=True).items():
        if value is not None:
            setattr(shift, key, value)

    await db.commit()
    await db.refresh(shift)
    return shift


@app.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: int,
    hard_delete: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a shift (manager only). Supports soft delete by default with optional permanent delete."""
    if current_user.user_type not in [UserType.ADMIN, UserType.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.execute(select(Shift).filter(Shift.id == shift_id))
    shift = result.scalar_one_or_none()
    
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    # Verify shift's role belongs to manager's department
    result = await db.execute(select(Role).filter(Role.id == shift.role_id))
    role = result.scalar_one_or_none()
    
    if current_user.user_type == UserType.MANAGER:
        manager_dept = await get_manager_department(current_user, db)
        if not manager_dept or role.department_id != manager_dept:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    if hard_delete:
        await db.delete(shift)
        await db.commit()
        return {"detail": "Shift permanently deleted"}
    
    if not shift.is_active:
        return {"detail": "Shift already inactive"}
    
    shift.is_active = False
    await db.commit()
    
    return {"detail": "Shift deleted successfully"}


@app.delete("/admin/roles/all")
async def delete_all_roles(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete all roles (admin only) - for testing/cleanup"""
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can perform this action")

    # Mark all roles as inactive
    result = await db.execute(select(Role).filter(Role.is_active == True))
    roles = result.scalars().all()

    count = 0
    for role in roles:
        role.is_active = False
        count += 1

    await db.commit()

    return {"message": f"Deleted {count} roles", "count": count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
