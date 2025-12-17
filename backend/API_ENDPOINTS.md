# API Endpoints Documentation

## Base URL
`http://localhost:8000`

## Authentication
All endpoints (except `/token`) require Bearer token in header:
```
Authorization: Bearer <token>
```

---

## 1. AUTHENTICATION

### Login (Get Token)
- **Endpoint**: `POST /token`
- **Auth**: No
- **Body**: 
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```

### Get Current User
- **Endpoint**: `GET /users/me`
- **Auth**: Yes
- **Response**: User details

---

## 2. USERS MANAGEMENT (Admin)

### Create User
- **Endpoint**: `POST /admin/users`
- **Auth**: Admin
- **Body**:
  ```json
  {
    "username": "newuser",
    "email": "user@example.com",
    "password": "password123",
    "full_name": "User Name",
    "role": "manager"
  }
  ```

### List All Users
- **Endpoint**: `GET /admin/users`
- **Auth**: Admin

### Delete User
- **Endpoint**: `DELETE /admin/users/{id}`
- **Auth**: Admin

---

## 3. DEPARTMENTS

### Create Department
- **Endpoint**: `POST /departments`
- **Auth**: Admin
- **Body**:
  ```json
  {
    "name": "Assembly",
    "description": "Assembly line operations"
  }
  ```

### List Departments
- **Endpoint**: `GET /departments`
- **Auth**: Yes

### Search Department
- **Endpoint**: `GET /departments/search/{query}`
- **Auth**: Yes
- **Query**: name, dept_id (001, 002), or id

### Update Department
- **Endpoint**: `PUT /departments/{id}`
- **Auth**: Admin
- **Body**:
  ```json
  {
    "name": "Assembly Updated",
    "description": "Updated description"
  }
  ```

### Delete Department
- **Endpoint**: `DELETE /departments/{id}`
- **Auth**: Admin

---

## 4. MANAGERS

### Create Manager (with reassign confirmation)
- **Endpoint**: `POST /managers`
- **Auth**: Admin
- **Query Params**: `force_reassign=true/false`
- **Body**:
  ```json
  {
    "user_id": 2,
    "department_id": 1,
    "manager_emp_id": "10001",
    "manager_dept_id": "001"
  }
  ```
- **Behavior**:
  - If manager exists for dept and `force_reassign=false`: Returns conflict response with old manager details
  - If `force_reassign=true`: Unassigns old manager (sets dept_id to NULL) and assigns new manager
  - Returns `status: "success"` or `status: "conflict"`

### List Managers
- **Endpoint**: `GET /managers`
- **Auth**: Admin
- **Returns**: All active managers (including unassigned ones)

### Update Manager
- **Endpoint**: `PUT /managers/{id}`
- **Auth**: Admin
- **Body**:
  ```json
  {
    "department_id": 2,
    "manager_emp_id": "10001",
    "manager_dept_id": "002"
  }
  ```

### Reassign Manager
- **Endpoint**: `PUT /managers/{id}/reassign`
- **Auth**: Admin
- **Body**: Same as update
- **Behavior**: Unassigns old manager from dept before reassigning

### Delete Manager
- **Endpoint**: `DELETE /managers/{id}`
- **Auth**: Admin

---

## 5. EMPLOYEES

### Create Employee
- **Endpoint**: `POST /employees`
- **Auth**: Manager
- **Body**:
  ```json
  {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "phone": "+1-555-0101",
    "address": "123 Main St",
    "department_id": 1,
    "role_id": 1,
    "weekly_hours": 40,
    "daily_max_hours": 8,
    "shifts_per_week": 5
  }
  ```

### List Employees
- **Endpoint**: `GET /employees`
- **Auth**: Yes
- **Behavior**: 
  - Admin: sees all
  - Manager: sees own department
  - Employee: sees self

### Update Employee
- **Endpoint**: `PUT /employees/{id}`
- **Auth**: Manager

### Delete Employee
- **Endpoint**: `DELETE /employees/{id}`
- **Auth**: Manager

---

## 6. ROLES (Shift Types)

### Create Role
- **Endpoint**: `POST /roles`
- **Auth**: Manager
- **Body**:
  ```json
  {
    "name": "Day Shift",
    "description": "Morning shift",
    "department_id": 1,
    "start_time": "05:00",
    "end_time": "14:00",
    "required_count": 5,
    "priority": 70,
    "required_skills": ["assembly"],
    "break_minutes": 60,
    "weekend_required": false,
    "schedule_config": {
      "Monday": {"enabled": true, "startTime": "05:00", "endTime": "14:00"}
    }
  }
  ```

### List Roles
- **Endpoint**: `GET /roles`
- **Auth**: Yes

---

## 7. SCHEDULES

### Create Schedule
- **Endpoint**: `POST /schedules`
- **Auth**: Manager
- **Body**:
  ```json
  {
    "employee_id": 1,
    "role_id": 1,
    "date": "2025-12-20",
    "start_time": "05:00",
    "end_time": "14:00",
    "notes": "Regular shift"
  }
  ```

### Get Schedules
- **Endpoint**: `GET /schedules`
- **Auth**: Yes
- **Query Params**: `start_date`, `end_date`
- **Behavior**: Filtered by role

### Update Schedule
- **Endpoint**: `PUT /schedules/{id}`
- **Auth**: Manager

### Delete Schedule
- **Endpoint**: `DELETE /schedules/{id}`
- **Auth**: Manager

### Generate Schedules (Auto)
- **Endpoint**: `POST /schedules/generate`
- **Auth**: Manager
- **Body**:
  ```json
  {
    "start_date": "2025-12-20",
    "end_date": "2025-12-31"
  }
  ```

### Check Schedule Conflicts
- **Endpoint**: `GET /schedules/conflicts`
- **Auth**: Manager
- **Query Params**: `start_date`, `end_date`

---

## 8. CHECK-IN/OUT

### Check In
- **Endpoint**: `POST /employee/check-in`
- **Auth**: Employee
- **Body**:
  ```json
  {
    "location": "Factory Floor A"
  }
  ```

### Check Out
- **Endpoint**: `POST /employee/check-out`
- **Auth**: Employee
- **Body**:
  ```json
  {
    "notes": "Shift completed"
  }
  ```

### Get Attendance
- **Endpoint**: `GET /attendance`
- **Auth**: Yes
- **Query Params**: `start_date`, `end_date`, `employee_id`

### Today's Attendance (Manager)
- **Endpoint**: `GET /attendance/today`
- **Auth**: Manager

### Attendance Stats
- **Endpoint**: `GET /attendance/stats`
- **Auth**: Yes
- **Query Params**: `start_date`, `end_date`

---

## 9. LEAVE REQUESTS

### Create Leave Request
- **Endpoint**: `POST /leave-requests`
- **Auth**: Employee/Manager
- **Body**:
  ```json
  {
    "employee_id": 1,
    "start_date": "2025-12-25",
    "end_date": "2025-12-26",
    "leave_type": "vacation",
    "reason": "Family trip"
  }
  ```

### List Leave Requests
- **Endpoint**: `GET /leave-requests`
- **Auth**: Yes
- **Behavior**: Filtered by role

### Approve Leave
- **Endpoint**: `POST /manager/approve-leave/{id}`
- **Auth**: Manager
- **Body**:
  ```json
  {
    "review_notes": "Approved"
  }
  ```

### Reject Leave
- **Endpoint**: `POST /manager/reject-leave/{id}`
- **Auth**: Manager
- **Body**:
  ```json
  {
    "review_notes": "Not approved"
  }
  ```

---

## 10. MESSAGES

### Send Message
- **Endpoint**: `POST /messages`
- **Auth**: Yes
- **Body**:
  ```json
  {
    "recipient_id": 2,
    "department_id": 1,
    "subject": "Shift Update",
    "message": "Message content"
  }
  ```

### Get Messages
- **Endpoint**: `GET /messages`
- **Auth**: Yes

### Delete Message
- **Endpoint**: `DELETE /messages/{id}`
- **Auth**: Yes

---

## 11. NOTIFICATIONS

### Get Notifications
- **Endpoint**: `GET /notifications`
- **Auth**: Yes
- **Query Params**: `unread_only=true/false`

### Mark as Read
- **Endpoint**: `POST /notifications/{id}/mark-read`
- **Auth**: Yes

### Mark All as Read
- **Endpoint**: `POST /notifications/mark-all-read`
- **Auth**: Yes

### Delete Notification
- **Endpoint**: `DELETE /notifications/{id}`
- **Auth**: Yes

---

## Error Responses

### Common Error Codes
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `409`: Conflict (e.g., manager already assigned)
- `500`: Server Error

### Error Response Format
```json
{
  "detail": "Error message"
}
```

---

## Testing Notes

- Get token first from `/token` endpoint
- Use token in all other requests
- Admin credentials: `admin` / `admin123`
- Manager credentials: `manager1` / `manager123`
- Employee credentials: `john.smith` / `employee123`
