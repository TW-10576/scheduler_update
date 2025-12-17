import React, { useState, useEffect } from 'react';
import { AlertCircle, X, Copy } from 'lucide-react';
import { format, addDays, startOfWeek } from 'date-fns';

const ShiftAssignmentWithDragDrop = ({ 
  employees = [], 
  roles = [], 
  schedules = [], 
  leaveRequests = [], 
  unavailability = [], 
  onShiftAssigned = () => {} 
}) => {
  const [currentWeekStart, setCurrentWeekStart] = useState(startOfWeek(new Date(), { weekStartsOn: 1 }));
  const [draggedShift, setDraggedShift] = useState(null);
  const [validationError, setValidationError] = useState(null);
  const [ruleViolations, setRuleViolations] = useState([]);
  const [scheduleData, setScheduleData] = useState(schedules);
  const [selectedRole, setSelectedRole] = useState(null);

  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const weekDates = Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart, i));

  // ==================== RULES VALIDATION ====================

  const checkConsecutiveShifts = (employeeId, fromDate) => {
    /**
     * Rule: No more than 5 consecutive shifts
     * Check if adding a shift would exceed 5 consecutive shifts
     */
    const consecutiveCount = { forward: 0, backward: 0 };
    const dateIndex = weekDates.findIndex(d => format(d, 'yyyy-MM-dd') === format(fromDate, 'yyyy-MM-dd'));

    if (dateIndex === -1) return false;

    // Check forward
    for (let i = dateIndex; i < 7; i++) {
      const date = format(weekDates[i], 'yyyy-MM-dd');
      const hasShift = scheduleData[date]?.[employeeId]?.length > 0;
      if (hasShift) {
        consecutiveCount.forward++;
      } else {
        break;
      }
    }

    // Check backward
    for (let i = dateIndex - 1; i >= 0; i--) {
      const date = format(weekDates[i], 'yyyy-MM-dd');
      const hasShift = scheduleData[date]?.[employeeId]?.length > 0;
      if (hasShift) {
        consecutiveCount.backward++;
      } else {
        break;
      }
    }

    const totalConsecutive = consecutiveCount.forward + consecutiveCount.backward;
    return totalConsecutive < 5; // Return true if adding shift is OK
  };

  const checkWeekendRestriction = (roleId, date) => {
    /**
     * Rule: Weekend work only if role has weekend_required = true
     */
    const role = roles.find(r => r.id === roleId);
    const dayOfWeek = new Date(date).getDay();
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

    if (isWeekend && role && !role.weekend_required) {
      return false; // Violation
    }
    return true; // OK
  };

  const checkAvailability = (employeeId, date) => {
    /**
     * Rule 1: Check if employee is on LEAVE
     * Rule 2: Check if employee is UNAVAILABLE
     */
    const dateStr = format(date, 'yyyy-MM-dd');
    const isOnLeave = leaveRequests[`${employeeId}-${dateStr}`]?.status === 'approved';
    const isUnavailable = unavailability[`${employeeId}-${dateStr}`];

    return { isOnLeave, isUnavailable };
  };

  const validateShiftAssignment = (employeeId, roleId, date) => {
    const violations = [];
    const dateStr = format(date, 'yyyy-MM-dd');

    // Check 1: Availability
    const { isOnLeave, isUnavailable } = checkAvailability(employeeId, date);
    if (isOnLeave) {
      violations.push({
        type: 'leave',
        message: 'Employee is on leave this day',
        severity: 'error',
        rule: 'Leave Rule'
      });
    }
    if (isUnavailable) {
      violations.push({
        type: 'unavailable',
        message: 'Employee is unavailable (will reassign shift)',
        severity: 'warning',
        rule: 'Unavailability Rule'
      });
    }

    // Check 2: Consecutive shifts (max 5)
    if (!checkConsecutiveShifts(employeeId, date)) {
      violations.push({
        type: 'consecutive',
        message: 'Would exceed maximum 5 consecutive shifts',
        severity: 'error',
        rule: '5 Shift Limit'
      });
    }

    // Check 3: Weekend restriction
    if (!checkWeekendRestriction(roleId, date)) {
      violations.push({
        type: 'weekend',
        message: 'Weekend work not allowed for this role',
        severity: 'error',
        rule: 'Weekend Restriction'
      });
    }

    return violations;
  };

  // ==================== DRAG AND DROP ====================

  const handleDragStart = (e, shift, employeeId) => {
    setDraggedShift({ shift, employeeId });
    setValidationError(null);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e, newEmployeeId, newDate) => {
    e.preventDefault();

    if (!draggedShift) return;

    const { shift, employeeId: oldEmployeeId } = draggedShift;
    const dateStr = format(newDate, 'yyyy-MM-dd');

    // Validate the new assignment
    const violations = validateShiftAssignment(newEmployeeId, shift.role_id, newDate);
    const errors = violations.filter(v => v.severity === 'error');
    const warnings = violations.filter(v => v.severity === 'warning');

    if (errors.length > 0) {
      // Show error popup with violations
      setValidationError({
        type: 'error',
        violations: errors,
        message: 'Cannot assign shift - rules violated'
      });
      setRuleViolations(errors);
      setDraggedShift(null);
      return;
    }

    // If only warnings, show confirmation
    if (warnings.length > 0) {
      const shouldContinue = window.confirm(
        `Warning: ${warnings.map(w => w.message).join('\n')}\n\nContinue anyway?`
      );
      if (!shouldContinue) {
        setDraggedShift(null);
        return;
      }
    }

    // Assign the shift
    const updatedSchedule = { ...scheduleData };
    if (!updatedSchedule[dateStr]) {
      updatedSchedule[dateStr] = {};
    }
    if (!updatedSchedule[dateStr][newEmployeeId]) {
      updatedSchedule[dateStr][newEmployeeId] = [];
    }

    updatedSchedule[dateStr][newEmployeeId].push(shift);

    // Remove from old location if different
    if (oldEmployeeId !== newEmployeeId || format(new Date(shift.date), 'yyyy-MM-dd') !== dateStr) {
      const oldDateStr = format(new Date(shift.date), 'yyyy-MM-dd');
      if (updatedSchedule[oldDateStr]?.[oldEmployeeId]) {
        updatedSchedule[oldDateStr][oldEmployeeId] = updatedSchedule[oldDateStr][oldEmployeeId].filter(s => s.id !== shift.id);
      }
    }

    setScheduleData(updatedSchedule);
    setDraggedShift(null);
    setValidationError(null);

    if (onShiftAssigned) {
      onShiftAssigned({
        employeeId: newEmployeeId,
        date: dateStr,
        shift: shift
      });
    }
  };

  const getEmployeeShiftsForDate = (employeeId, date) => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return scheduleData[dateStr]?.[employeeId] || [];
  };

  const getRoleName = (roleId) => {
    return roles.find(r => r.id === roleId)?.name || 'Unknown Role';
  };

  return (
    <div className="space-y-6">
      {/* Validation Error Popup */}
      {validationError?.type === 'error' && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-start gap-4">
              <AlertCircle size={24} className="text-red-600 flex-shrink-0 mt-1" />
              <div className="flex-1">
                <h3 className="font-bold text-lg text-gray-900">Cannot Assign Shift</h3>
                <p className="text-sm text-gray-600 mt-2">{validationError.message}</p>

                <div className="mt-4 space-y-2">
                  {ruleViolations.map((violation, idx) => (
                    <div key={idx} className="bg-red-50 border border-red-200 rounded p-2">
                      <div className="text-xs font-semibold text-red-800">{violation.rule}</div>
                      <div className="text-xs text-red-700">{violation.message}</div>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => {
                    setValidationError(null);
                    setRuleViolations([]);
                  }}
                  className="w-full mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium"
                >
                  Understood
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rules Information Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-3">
          <AlertCircle size={18} className="text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-semibold">Shift Assignment Rules:</p>
            <ul className="list-disc list-inside space-y-1 mt-2 text-xs">
              <li><strong>No Leave</strong>: Cannot assign to employees on approved leave</li>
              <li><strong>5 Shift Max</strong>: Maximum 5 consecutive shifts per employee</li>
              <li><strong>Weekend Restriction</strong>: Weekends only for roles with weekend_required enabled</li>
              <li><strong>Unavailability</strong>: If unavailable selected, shift will be reassigned to another day</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Calendar Grid */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Drag & Drop Shift Assignment</h2>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <td className="border border-gray-300 p-2 font-semibold bg-gray-50" style={{ minWidth: '150px' }}>
                  Employee
                </td>
                {weekDates.map((date, idx) => (
                  <td
                    key={idx}
                    className="border border-gray-300 p-2 text-center font-semibold bg-gray-50"
                    style={{ minWidth: '160px' }}
                  >
                    <div className="text-sm">{daysOfWeek[idx]}</div>
                    <div className="text-xs text-gray-600">{format(date, 'MMM dd')}</div>
                  </td>
                ))}
              </tr>
            </thead>

            <tbody>
              {employees.map(emp => (
                <tr key={emp.id} className="hover:bg-blue-50">
                  <td className="border border-gray-300 p-2 font-semibold text-gray-900 bg-gray-50 sticky left-0">
                    {emp.first_name} {emp.last_name}
                  </td>

                  {weekDates.map((date, idx) => {
                    const shifts = getEmployeeShiftsForDate(emp.id, date);
                    const dateStr = format(date, 'yyyy-MM-dd');
                    const { isOnLeave, isUnavailable } = checkAvailability(emp.id, date);

                    return (
                      <td
                        key={dateStr}
                        className={`border border-gray-300 p-2 min-h-24 align-top cursor-move transition ${
                          isOnLeave
                            ? 'bg-red-100'
                            : isUnavailable
                            ? 'bg-orange-100'
                            : 'bg-white'
                        }`}
                        onDragOver={handleDragOver}
                        onDrop={(e) => handleDrop(e, emp.id, date)}
                      >
                        {isOnLeave && (
                          <div className="text-center font-bold text-red-700 text-xs">LEAVE</div>
                        )}
                        {isUnavailable && (
                          <div className="text-center font-bold text-orange-700 text-xs">UNAVAIL</div>
                        )}

                        {shifts.length > 0 && !isOnLeave && !isUnavailable && (
                          <div className="space-y-1">
                            {shifts.map((shift, sIdx) => (
                              <div
                                key={sIdx}
                                draggable
                                onDragStart={(e) => handleDragStart(e, shift, emp.id)}
                                className="bg-green-100 border border-green-300 rounded p-1 text-xs cursor-grab active:cursor-grabbing hover:shadow-md transition"
                              >
                                <div className="font-semibold text-green-700 text-xs">
                                  {getRoleName(shift.role_id)}
                                </div>
                                <div className="text-green-600 font-mono text-xs">
                                  {shift.start_time} - {shift.end_time}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {shifts.length === 0 && !isOnLeave && !isUnavailable && (
                          <div className="text-center text-gray-400 text-xs">—</div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="mt-6 flex flex-wrap gap-4 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-green-100 border border-green-300 rounded"></div>
            <span>Shift (Drag to reassign)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-red-100 border border-red-300 rounded"></div>
            <span>Leave (No assignment)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-orange-100 border border-orange-300 rounded"></div>
            <span>Unavailable (Auto-reassign)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ShiftAssignmentWithDragDrop;
