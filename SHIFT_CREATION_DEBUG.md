# Shift Creation Debugging Guide

## Issues Fixed

1. ✅ **"Add Shift" button now inside role card** - Previously it was outside, now it's nested inside the selected role
2. ✅ **Better error handling** - Added validation and console logging for debugging
3. ✅ **Improved role loading** - Now properly fetches shifts with selectedRole
4. ✅ **Enhanced shift form validation** - Validates required fields before submission

---

## Testing Steps

### Step 1: Start Backend with Logging
```bash
cd /home/tw10519/attend/Major2-v6/backend
python -m uvicorn app.main:app --reload --port 8000
```

### Step 2: Start Frontend
```bash
cd /home/tw10519/attend/Major2-v6/frontend
npm run dev
```

### Step 3: Test in Browser

1. **Open Developer Console**
   - Press F12 or Ctrl+Shift+I
   - Go to "Console" tab

2. **Login as Manager**
   - Navigate to http://localhost:5173
   - Login with manager credentials

3. **Go to Manager Dashboard**
   - Click "Roles & Shifts Management"

4. **Create a Test Role**
   - Click "Add Role" button
   - Fill in:
     - Role Name: "Test Engineer"
     - Description: "Test role for shift creation"
     - Skills: "Testing, QA"
   - Click "Create Role"
   - **Check Console:** Should see "Loaded roles:" with the new role

5. **Click on Role to Select**
   - Click on the "Test Engineer" role card
   - It should highlight in blue
   - **Check Console:** Should see "Loading role details for: [ID]"
   - **Check UI:** Below the role, you should see "Shifts (0):" with "Add Shift" button

6. **Create First Shift**
   - Click "Add Shift" button inside the role
   - Modal should open: "Create Shift for Test Engineer"
   - Fill in:
     - Shift Name: "Morning Shift"
     - Start Time: 09:00
     - End Time: 17:00
     - Min Employees: 2
     - Max Employees: 5
     - Priority: 60
   - Click "Create Shift"
   - **Check Console:** Should see:
     ```
     Creating shift with: { name: "Morning Shift", ... role_id: [ID] }
     Shift created: { id: [ID], name: "Morning Shift", ... }
     Loaded roles: [...]
     Loaded role details: { ..., shifts: [...] }
     ```
   - **Check UI:**
     - Modal should close
     - Role card should now show "Shifts (1):"
     - The shift should appear in the nested list

7. **Create Another Shift**
   - Click "Add Shift" again
   - Fill in:
     - Shift Name: "Evening Shift"
     - Start Time: 17:00
     - End Time: 22:00
     - Min Employees: 1
     - Max Employees: 3
     - Priority: 50
   - Click "Create Shift"
   - **Check UI:** Role should now show "Shifts (2):" with both shifts

---

## What to Check in Console

### Successful Shift Creation Should Show:
```javascript
Creating shift with: {
  name: "Morning Shift",
  start_time: "09:00",
  end_time: "17:00",
  min_emp: 2,
  max_emp: 5,
  priority: 60,
  schedule_config: {},
  role_id: 1
}

// Then:
Shift created: {
  id: 123,
  name: "Morning Shift",
  start_time: "09:00",
  end_time: "17:00",
  min_emp: 2,
  max_emp: 5,
  priority: 60,
  is_active: true,
  ...
}

// Then:
Loaded role details: {
  id: 1,
  name: "Test Engineer",
  shifts: [
    {
      id: 123,
      name: "Morning Shift",
      start_time: "09:00",
      end_time: "17:00",
      ...
    }
  ]
}
```

### If Error Occurs, Check:

**Error: "Please select a role first"**
- Make sure you clicked on a role card to select it
- The card should highlight in blue
- selectedRole should have an id property

**Error: "Failed to save shift"**
- Check console for: `Shift error: [error details]`
- Verify role ID is being passed: `Creating shift with: { ... role_id: [ID] }`
- Check backend logs for error response

**Shift not appearing in UI**
- Check Console for: `Loaded role details:`
- Verify it has `shifts: [...]` array
- Shift should be in the array with correct id and name

**Shift count still showing 0**
- Check that loadRoles() is being called
- Check Console for: `Loaded role details: { ..., shifts: [...] }`
- The UI reads from `role.shifts?.length || 0`

---

## Backend API Check

### Test Shift Creation Directly

```bash
# Get token first (replace with your login)
TOKEN=$(curl -s -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager1&password=password123" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Get first role ID
ROLE_ID=$(curl -s -X GET "http://localhost:8000/roles" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

# Create shift
curl -s -X POST "http://localhost:8000/shifts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Test Shift\",
    \"role_id\": $ROLE_ID,
    \"start_time\": \"09:00\",
    \"end_time\": \"17:00\",
    \"min_emp\": 1,
    \"max_emp\": 5,
    \"priority\": 50,
    \"schedule_config\": {}
  }" | jq .

# Get role with shifts
curl -s -X GET "http://localhost:8000/roles/$ROLE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.shifts'
```

---

## Key Files Modified

1. **frontend/src/pages/Manager.jsx**
   - Added "Add Shift" button INSIDE role card (line 745-754)
   - Enhanced loadRoles() with better shift loading (line 527-556)
   - Added validation and logging to handleCreateShift (line 591-657)
   - Improved role detail loading with logging (line 725-735)

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| No "Add Shift" button | Click on a role card to select it first |
| Modal says "Create Shift for Role" | selectedRole.name wasn't loaded - click role again |
| Shift form won't submit | Check console for validation errors - all fields required |
| Shift count still 0 after creation | Check console for "Shift created" and "Loaded role details" logs |
| Get 404 on POST /shifts | Make sure role_id is being passed correctly |

---

## Expected Flow

```
1. Create Role
   ↓
2. Click Role Card to Select (should highlight blue)
   ↓
3. "Shifts (0):" appears with "Add Shift" button
   ↓
4. Click "Add Shift" (modal opens)
   ↓
5. Fill form and submit
   ↓
6. Console: "Creating shift with: { ... }"
   ↓
7. Console: "Shift created: { id: ..., name: ... }"
   ↓
8. Console: "Loaded role details: { ..., shifts: [...] }"
   ↓
9. UI: "Shifts (1):" with shift displayed
```

---

## Quick Test Command

After starting backend and frontend:

```bash
# Run the comprehensive test script
bash /home/tw10519/attend/Major2-v6/test_crud_operations.sh
```

This will test the entire flow including:
- Login
- Create role
- Create shifts
- Update shifts
- Delete shifts
- Delete roles
- Delete all roles

---

## Still Having Issues?

If shifts still aren't being created:

1. **Check Backend Logs** - Look for error messages in backend terminal
2. **Check Browser Console** - Press F12, go to Console tab, look for red errors
3. **Check Network Tab** - Go to Network tab, click "Create Shift", check POST request
4. **Verify Role Selection** - Make sure selectedRole has an `id` property before creating shift

The console logging will help identify exactly where the issue is in the flow.
