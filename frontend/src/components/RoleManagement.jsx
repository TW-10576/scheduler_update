import React, { useState, useEffect } from 'react';
import { Plus, Edit2, Trash2, X, AlertCircle } from 'lucide-react';
import { createRole, listRoles, updateRole, deleteRole } from '../services/api';

const RoleManagement = () => {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showRoleForm, setShowRoleForm] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [validationErrors, setValidationErrors] = useState({});

  const [roleForm, setRoleForm] = useState({
    name: '',
    description: '',
    department_id: 1,
    start_time: '09:00',
    end_time: '17:00',
    required_count: 1,
    priority: 50,
    priority_percentage: 50,
    break_minutes: 60,
    weekend_required: false,
    required_skills: []
  });

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    try {
      setLoading(true);
      const response = await listRoles();
      const rolesData = response?.data || response || [];
      setRoles(Array.isArray(rolesData) ? rolesData : []);
    } catch (err) {
      setError('Failed to load roles');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!roleForm.name.trim()) {
      errors.name = 'Role name is required';
    }

    if (roleForm.priority < 1 || roleForm.priority > 100) {
      errors.priority = 'Priority must be between 1-100';
    }

    if (roleForm.priority_percentage < 1 || roleForm.priority_percentage > 100) {
      errors.priority_percentage = 'Priority percentage must be between 1-100';
    }

    if (roleForm.break_minutes < 0 || roleForm.break_minutes > 240) {
      errors.break_minutes = 'Break hours must be 0-4 hours (0-240 minutes)';
    }

    if (roleForm.required_count < 1) {
      errors.required_count = 'Required count must be at least 1';
    }

    // Validate start and end times
    const [startH, startM] = roleForm.start_time.split(':').map(Number);
    const [endH, endM] = roleForm.end_time.split(':').map(Number);
    const startTotalMin = startH * 60 + startM;
    const endTotalMin = endH * 60 + endM;

    if (startTotalMin >= endTotalMin) {
      errors.times = 'End time must be after start time';
    }

    // Calculate shift duration
    let shiftDuration = endTotalMin - startTotalMin;
    if (shiftDuration < 0) shiftDuration += 24 * 60;

    // If shift > 4 hours, break time is required
    if (shiftDuration > 240 && roleForm.break_minutes === 0) {
      errors.break_minutes = 'Shifts longer than 4 hours require a break time';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSaveRole = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!validateForm()) {
      return;
    }

    try {
      const roleData = {
        name: roleForm.name,
        description: roleForm.description,
        department_id: roleForm.department_id,
        start_time: roleForm.start_time,
        end_time: roleForm.end_time,
        required_count: roleForm.required_count,
        priority: roleForm.priority,
        priority_percentage: roleForm.priority_percentage,
        break_minutes: roleForm.break_minutes,
        weekend_required: roleForm.weekend_required,
        required_skills: roleForm.required_skills
      };

      if (editingRole) {
        await updateRole(editingRole.id, roleData);
        setSuccess('Role updated successfully');
      } else {
        await createRole(roleData);
        setSuccess('Role created successfully');
      }

      setShowRoleForm(false);
      setEditingRole(null);
      setRoleForm({
        name: '',
        description: '',
        department_id: 1,
        start_time: '09:00',
        end_time: '17:00',
        required_count: 1,
        priority: 50,
        priority_percentage: 50,
        break_minutes: 60,
        weekend_required: false,
        required_skills: []
      });

      await loadRoles();
    } catch (err) {
      setError(err.message || 'Failed to save role');
    }
  };

  const handleEditRole = (role) => {
    setEditingRole(role);
    setRoleForm({
      name: role.name,
      description: role.description || '',
      department_id: role.department_id,
      start_time: role.start_time,
      end_time: role.end_time,
      required_count: role.required_count,
      priority: role.priority || 50,
      priority_percentage: role.priority_percentage || 50,
      break_minutes: role.break_minutes || 60,
      weekend_required: role.weekend_required || false,
      required_skills: role.required_skills || []
    });
    setShowRoleForm(true);
  };

  const handleDeleteRole = async (id) => {
    if (!window.confirm('Are you sure you want to delete this role?')) {
      return;
    }

    try {
      await deleteRole(id);
      setSuccess('Role deleted successfully');
      await loadRoles();
    } catch (err) {
      setError('Failed to delete role');
    }
  };

  const calculateShiftDuration = () => {
    const [startH, startM] = roleForm.start_time.split(':').map(Number);
    const [endH, endM] = roleForm.end_time.split(':').map(Number);
    const startTotalMin = startH * 60 + startM;
    let endTotalMin = endH * 60 + endM;

    if (endTotalMin < startTotalMin) endTotalMin += 24 * 60;

    const totalMin = endTotalMin - startTotalMin;
    const breakMin = roleForm.break_minutes;
    const workMin = Math.max(0, totalMin - breakMin);

    return {
      total: (totalMin / 60).toFixed(1),
      break: (breakMin / 60).toFixed(1),
      work: (workMin / 60).toFixed(1)
    };
  };

  const duration = calculateShiftDuration();

  return (
    <div className="space-y-6">
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-green-800">
          {success}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Role Management</h2>
            <p className="text-sm text-gray-600 mt-1">Create and manage job roles with priority distribution</p>
          </div>
          <button
            onClick={() => {
              setEditingRole(null);
              setRoleForm({
                name: '',
                description: '',
                department_id: 1,
                start_time: '09:00',
                end_time: '17:00',
                required_count: 1,
                priority: 50,
                priority_percentage: 50,
                break_minutes: 60,
                weekend_required: false,
                required_skills: []
              });
              setValidationErrors({});
              setShowRoleForm(true);
            }}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-2"
          >
            <Plus size={18} />
            Create Role
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading roles...</div>
        ) : roles.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No roles created yet. Create one to get started!</div>
        ) : (
          <div className="space-y-4">
            {roles.map(role => (
              <div key={role.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg text-gray-900">{role.name}</h3>
                    {role.description && (
                      <p className="text-sm text-gray-600 mt-1">{role.description}</p>
                    )}

                    <div className="grid grid-cols-6 gap-3 mt-3">
                      <div className="bg-blue-50 rounded p-2">
                        <div className="text-xs text-blue-600 font-semibold">Priority</div>
                        <div className="text-sm font-bold text-blue-900">{role.priority}%</div>
                      </div>
                      <div className="bg-purple-50 rounded p-2">
                        <div className="text-xs text-purple-600 font-semibold">Distribution</div>
                        <div className="text-sm font-bold text-purple-900">{role.priority_percentage || role.priority}%</div>
                      </div>
                      {(() => {
                        // Calculate shift duration from start_time and end_time
                        const [startH, startM] = (role.start_time || '09:00').split(':').map(Number);
                        const [endH, endM] = (role.end_time || '17:00').split(':').map(Number);
                        const totalHours = (endH + endM / 60) - (startH + startM / 60);
                        const breakHours = (role.break_minutes || 0) / 60;
                        const workHours = totalHours - breakHours;

                        return (
                          <>
                            <div className="bg-blue-50 rounded p-2">
                              <div className="text-xs text-blue-600 font-semibold">Total Time</div>
                              <div className="text-sm font-bold text-blue-900">{totalHours.toFixed(1)} hrs</div>
                            </div>
                            <div className="bg-orange-50 rounded p-2">
                              <div className="text-xs text-orange-600 font-semibold">Break Time</div>
                              <div className="text-sm font-bold text-orange-900">{breakHours.toFixed(1)} hrs</div>
                            </div>
                            <div className="bg-green-50 rounded p-2">
                              <div className="text-xs text-green-600 font-semibold">Work Hours</div>
                              <div className="text-sm font-bold text-green-900">{workHours.toFixed(1)} hrs</div>
                            </div>
                          </>
                        );
                      })()}
                      <div className="bg-cyan-50 rounded p-2">
                        <div className="text-xs text-cyan-600 font-semibold">Required Count</div>
                        <div className="text-sm font-bold text-cyan-900">{role.required_count}</div>
                      </div>
                      <div className={`rounded p-2 ${role.weekend_required ? 'bg-red-50' : 'bg-gray-50'}`}>
                        <div className={`text-xs font-semibold ${role.weekend_required ? 'text-red-600' : 'text-gray-600'}`}>
                          Weekends
                        </div>
                        <div className={`text-sm font-bold ${role.weekend_required ? 'text-red-900' : 'text-gray-900'}`}>
                          {role.weekend_required ? 'Required' : 'Not Required'}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 text-xs text-gray-600">
                      <span>{role.start_time} - {role.end_time}</span>
                      {role.required_skills && role.required_skills.length > 0 && (
                        <div className="mt-2">
                          <span className="font-semibold">Skills:</span> {role.required_skills.join(', ')}
                        </div>
                      )}
                    </div>

                    {role.shifts && role.shifts.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <h4 className="text-sm font-semibold text-gray-900 mb-3">Shifts</h4>
                        <div className="grid grid-cols-1 gap-3">
                          {role.shifts.map(shift => (
                            <div key={shift.id} className="border border-gray-200 rounded p-3 bg-gray-50">
                              <div className="flex justify-between items-start mb-2">
                                <div className="font-semibold text-sm text-gray-900">{shift.name}</div>
                                <div className="text-xs text-gray-600">{shift.start_time} - {shift.end_time}</div>
                              </div>

                              <div className="grid grid-cols-3 gap-2">
                                {(() => {
                                  const [startH, startM] = shift.start_time.split(':').map(Number);
                                  const [endH, endM] = shift.end_time.split(':').map(Number);
                                  const shiftTotalHours = (endH + endM / 60) - (startH + startM / 60);
                                  const breakHours = (role.break_minutes || 0) / 60;
                                  const workHours = shiftTotalHours - breakHours;

                                  return (
                                    <>
                                      <div className="bg-blue-100 rounded p-1.5">
                                        <div className="text-xs text-blue-700 font-semibold">Total Time</div>
                                        <div className="text-xs font-bold text-blue-900">{shiftTotalHours.toFixed(1)} hrs</div>
                                      </div>
                                      <div className="bg-orange-100 rounded p-1.5">
                                        <div className="text-xs text-orange-700 font-semibold">Break</div>
                                        <div className="text-xs font-bold text-orange-900">{breakHours.toFixed(1)} hrs</div>
                                      </div>
                                      <div className="bg-green-100 rounded p-1.5">
                                        <div className="text-xs text-green-700 font-semibold">Work Hours</div>
                                        <div className="text-xs font-bold text-green-900">{workHours.toFixed(1)} hrs</div>
                                      </div>
                                    </>
                                  );
                                })()}
                              </div>

                              <div className="text-xs text-gray-600 mt-2">
                                <span className="text-gray-700 font-semibold">Employees:</span> {shift.min_emp} - {shift.max_emp}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleEditRole(role)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
                    >
                      <Edit2 size={18} />
                    </button>
                    <button
                      onClick={() => handleDeleteRole(role.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Role Form Modal */}
      {showRoleForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-96 overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-900">
                {editingRole ? 'Edit Role' : 'Create New Role'}
              </h2>
              <button
                onClick={() => {
                  setShowRoleForm(false);
                  setEditingRole(null);
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={24} />
              </button>
            </div>

            <form onSubmit={handleSaveRole} className="space-y-4">
              {/* Role Name */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-1">
                  Role Name *
                </label>
                <input
                  type="text"
                  value={roleForm.name}
                  onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                    validationErrors.name ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                  }`}
                  placeholder="e.g., Day Shift Manager"
                />
                {validationErrors.name && (
                  <p className="text-sm text-red-600 mt-1">{validationErrors.name}</p>
                )}
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-1">
                  Description
                </label>
                <textarea
                  value={roleForm.description}
                  onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Role description"
                  rows="2"
                />
              </div>

              {/* Time and Hours */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Start Time *
                  </label>
                  <input
                    type="time"
                    value={roleForm.start_time}
                    onChange={(e) => setRoleForm({ ...roleForm, start_time: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    End Time *
                  </label>
                  <input
                    type="time"
                    value={roleForm.end_time}
                    onChange={(e) => setRoleForm({ ...roleForm, end_time: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Total Hours
                  </label>
                  <div className="px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-900 font-semibold">
                    {duration.total}h
                  </div>
                </div>
              </div>
              {validationErrors.times && (
                <p className="text-sm text-red-600">{validationErrors.times}</p>
              )}

              {/* Break Time and Work Hours */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Break Time (hrs) *
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="4"
                    step="0.25"
                    value={roleForm.break_minutes / 60}
                    onChange={(e) => setRoleForm({ ...roleForm, break_minutes: parseInt(e.target.value * 60) })}
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                      validationErrors.break_minutes ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                    placeholder="1"
                  />
                  {validationErrors.break_minutes && (
                    <p className="text-sm text-red-600 mt-1">{validationErrors.break_minutes}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">Default: 1 hour</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Work Hours
                  </label>
                  <div className="px-3 py-2 border border-gray-300 rounded-lg bg-green-50 text-green-900 font-semibold">
                    {duration.work}h
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Break Hours
                  </label>
                  <div className="px-3 py-2 border border-gray-300 rounded-lg bg-orange-50 text-orange-900 font-semibold">
                    {duration.break}h
                  </div>
                </div>
              </div>

              {/* Priority Settings */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Priority Level (1-100) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={roleForm.priority}
                    onChange={(e) => setRoleForm({ ...roleForm, priority: parseInt(e.target.value) })}
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                      validationErrors.priority ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                  />
                  {validationErrors.priority && (
                    <p className="text-sm text-red-600 mt-1">{validationErrors.priority}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">Higher = more shifts assigned</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-1">
                    Distribution % (1-100) *
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={roleForm.priority_percentage}
                    onChange={(e) => setRoleForm({ ...roleForm, priority_percentage: parseInt(e.target.value) })}
                    className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                      validationErrors.priority_percentage ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                  />
                  {validationErrors.priority_percentage && (
                    <p className="text-sm text-red-600 mt-1">{validationErrors.priority_percentage}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">Percentage of total shifts</p>
                </div>
              </div>

              {/* Required Count */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-1">
                  Required Employees *
                </label>
                <input
                  type="number"
                  min="1"
                  value={roleForm.required_count}
                  onChange={(e) => setRoleForm({ ...roleForm, required_count: parseInt(e.target.value) })}
                  className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 ${
                    validationErrors.required_count ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                  }`}
                />
                {validationErrors.required_count && (
                  <p className="text-sm text-red-600 mt-1">{validationErrors.required_count}</p>
                )}
              </div>

              {/* Weekend Requirement */}
              <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200">
                <input
                  type="checkbox"
                  id="weekendRequired"
                  checked={roleForm.weekend_required}
                  onChange={(e) => setRoleForm({ ...roleForm, weekend_required: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <label htmlFor="weekendRequired" className="text-sm font-medium text-gray-900">
                  Weekend Work Required
                </label>
                <p className="text-xs text-gray-600 ml-auto">If checked, employees can be assigned weekends</p>
              </div>

              {/* Info Box */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="flex gap-2">
                  <AlertCircle size={16} className="text-blue-600 flex-shrink-0 mt-0.5" />
                  <div className="text-xs text-blue-800">
                    <p className="font-semibold">Schedule Rules:</p>
                    <ul className="list-disc list-inside space-y-1 mt-1">
                      <li>Max 5 consecutive shifts per employee</li>
                      <li>Weekend assignments only if enabled</li>
                      <li>Shifts over 4 hours require break time</li>
                      <li>Unavailability shifts auto-reassigned</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Buttons */}
              <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => {
                    setShowRoleForm(false);
                    setEditingRole(null);
                  }}
                  className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium"
                >
                  {editingRole ? 'Update Role' : 'Create Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default RoleManagement;
