import React, { useState, useEffect } from 'react';
import { Calendar, Plus, Edit2, Trash2, Check, X, Clock, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import Card from './common/Card';
import Button from './common/Button';
import Modal from './common/Modal';
import { getSchedules, createSchedule, updateSchedule, deleteSchedule, generateSchedule } from '../services/api';
import api from '../services/api';

const ScheduleManager = ({ departmentId, employees = [], roles = [] }) => {
  // View/Edit Mode
  const [viewMode, setViewMode] = useState('view');
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentWeekStart, setCurrentWeekStart] = useState(getMonday(new Date()));
  const [leaveRequests, setLeaveRequests] = useState({});

  // Modals
  const [showWeekPicker, setShowWeekPicker] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [selectedWeek, setSelectedWeek] = useState(getMonday(new Date()));

  // Edit mode state
  const [editedSchedules, setEditedSchedules] = useState([]);
  const [draggedSchedule, setDraggedSchedule] = useState(null);
  const [editingScheduleId, setEditingScheduleId] = useState(null);
  const [editingTimes, setEditingTimes] = useState(null);

  // Error/Success
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Get Monday of week
  function getMonday(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff)).toISOString().split('T')[0];
  }

  // Get week dates
  function getWeekDates(mondayDate) {
    const dates = [];
    const start = new Date(mondayDate);
    for (let i = 0; i < 7; i++) {
      const date = new Date(start);
      date.setDate(date.getDate() + i);
      dates.push(date.toISOString().split('T')[0]);
    }
    return dates;
  }

  // Load schedules
  useEffect(() => {
    loadSchedulesForWeek();
  }, [currentWeekStart, viewMode]);

  const loadSchedulesForWeek = async () => {
    setLoading(true);
    try {
      const weekDates = getWeekDates(currentWeekStart);
      const startDate = weekDates[0];
      const endDate = weekDates[6];
      const response = await getSchedules(startDate, endDate);
      setSchedules(response.data || []);
      setEditedSchedules(JSON.parse(JSON.stringify(response.data || [])));

      // Fetch leave requests
      const leavesRes = await api.get('/leave-requests');
      if (leavesRes.data) {
        const leavesByKey = {};
        leavesRes.data.forEach(leave => {
          if (leave.status === 'approved') {
            // Expand date range
            const startDate = new Date(leave.start_date + 'T00:00:00');
            const endDate = new Date(leave.end_date + 'T00:00:00');

            for (let currentDate = new Date(startDate);
                 currentDate <= endDate;
                 currentDate.setDate(currentDate.getDate() + 1)) {
              const dateStr = currentDate.toISOString().split('T')[0];
              leavesByKey[`${leave.employee_id}-${dateStr}`] = leave;
            }
          }
        });
        setLeaveRequests(leavesByKey);
      }
    } catch (error) {
      console.error('Failed to load schedules:', error);
      setError('Failed to load schedules');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSchedule = async () => {
    setLoading(true);
    try {
      const weekDates = getWeekDates(selectedWeek);
      const startDate = weekDates[0];
      const endDate = weekDates[6];

      console.log('Generating schedules for', startDate, 'to', endDate);
      const response = await generateSchedule(startDate, endDate);
      console.log('Generation response:', response);

      // Show feedback from backend
      const scheduleCount = response.data?.schedules_created || 0;
      const feedback = response.data?.feedback || [];

      if (scheduleCount > 0) {
        setSuccess(`✅ Generated ${scheduleCount} schedules!\n${feedback.join('\n')}`);
      } else {
        setError(`⚠️ No schedules generated.\n${feedback.join('\n')}`);
      }

      setTimeout(() => {
        setSuccess('');
        setError('');
      }, 5000);

      setShowWeekPicker(false);
      setCurrentWeekStart(selectedWeek);

      // Wait a moment then reload
      setTimeout(() => loadSchedulesForWeek(), 500);
    } catch (error) {
      console.error('Generation error:', error);
      setError('Failed to generate schedule: ' + (error.response?.data?.detail || error.message));
      setTimeout(() => setError(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSchedule = () => {
    const newSchedule = {
      id: `new-${Date.now()}`,
      employee_id: employees[0]?.id || '',
      role_id: roles[0]?.id || '',
      date: getWeekDates(currentWeekStart)[0],
      start_time: '09:00',
      end_time: '17:00',
      shift_id: null,
      status: 'scheduled',
      isNew: true
    };
    setEditedSchedules([...editedSchedules, newSchedule]);
  };

  const handleDeleteScheduleEdit = (scheduleId) => {
    setEditedSchedules(editedSchedules.filter(s => s.id !== scheduleId));
  };

  const handleEditTimes = (schedule) => {
    setEditingScheduleId(schedule.id);
    setEditingTimes({ ...schedule });
  };

  const handleSaveTimes = () => {
    if (editingTimes) {
      setEditedSchedules(editedSchedules.map(s =>
        s.id === editingTimes.id
          ? { ...s, start_time: editingTimes.start_time, end_time: editingTimes.end_time }
          : s
      ));
    }
    setEditingScheduleId(null);
    setEditingTimes(null);
  };

  const handleConfirmChanges = async () => {
    setLoading(true);
    try {
      // Delete old schedules
      const deleteTasks = schedules
        .filter(s => !editedSchedules.find(e => e.id === s.id))
        .map(s => deleteSchedule(s.id));

      // Create new schedules
      const createTasks = editedSchedules
        .filter(s => s.isNew)
        .map(s => createSchedule({
          employee_id: s.employee_id,
          role_id: s.role_id,
          date: s.date,
          start_time: s.start_time,
          end_time: s.end_time,
          shift_id: s.shift_id
        }));

      // Update existing
      const updateTasks = editedSchedules
        .filter(s => !s.isNew && schedules.find(orig => orig.id === s.id))
        .map(s => updateSchedule(s.id, {
          employee_id: s.employee_id,
          role_id: s.role_id,
          date: s.date,
          start_time: s.start_time,
          end_time: s.end_time,
          shift_id: s.shift_id
        }));

      await Promise.all([...deleteTasks, ...createTasks, ...updateTasks]);

      setSuccess('✅ Schedule changes saved!');
      setTimeout(() => setSuccess(''), 3000);
      setViewMode('view');
      await loadSchedulesForWeek();
    } catch (error) {
      setError('Failed to save schedule: ' + (error.response?.data?.detail || error.message));
      setTimeout(() => setError(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  const getEmployeeName = (empId) => {
    const emp = employees.find(e => e.id === empId);
    return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
  };

  const getRoleName = (roleId) => {
    const role = roles.find(r => r.id === roleId);
    return role?.name || 'Unknown';
  };

  const getRoleColor = (roleId) => {
    const colors = [
      'bg-blue-100 text-blue-900',
      'bg-purple-100 text-purple-900',
      'bg-pink-100 text-pink-900',
      'bg-green-100 text-green-900',
      'bg-yellow-100 text-yellow-900',
      'bg-indigo-100 text-indigo-900'
    ];
    return colors[roleId % colors.length];
  };

  const isOnLeave = (employeeId, date) => {
    return !!leaveRequests[`${employeeId}-${date}`];
  };

  const weekDates = getWeekDates(currentWeekStart);
  const displaySchedules = viewMode === 'edit' ? editedSchedules : schedules;

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const handlePreviousWeek = () => {
    setCurrentWeekStart(getMonday(new Date(currentWeekStart).getTime() - 7 * 24 * 60 * 60 * 1000));
  };

  const handleNextWeek = () => {
    setCurrentWeekStart(getMonday(new Date(currentWeekStart).getTime() + 7 * 24 * 60 * 60 * 1000));
  };

  return (
    <div>
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start">
          <AlertCircle className="w-5 h-5 text-red-500 mr-3 flex-shrink-0 mt-0.5" />
          <span className="text-sm text-red-700 whitespace-pre-wrap">{error}</span>
        </div>
      )}
      {success && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-start">
          <Check className="w-5 h-5 text-green-500 mr-3 flex-shrink-0 mt-0.5" />
          <span className="text-sm text-green-700 whitespace-pre-wrap">{success}</span>
        </div>
      )}

      <Card
        title="Schedule Management"
        subtitle={`Week of ${weekDates[0]} to ${weekDates[6]}`}
        headerAction={
          viewMode === 'view' ? (
            <div className="flex gap-2 items-center">
              <button onClick={handlePreviousWeek} className="p-2 hover:bg-gray-100 rounded">
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-sm font-medium min-w-[200px] text-center">{weekDates[0]} to {weekDates[6]}</span>
              <button onClick={handleNextWeek} className="p-2 hover:bg-gray-100 rounded">
                <ChevronRight className="w-5 h-5" />
              </button>
              <div className="border-l pl-2 ml-2 flex gap-2">
                <Button onClick={() => setShowWeekPicker(true)} variant="primary">
                  <Calendar className="w-4 h-4 mr-2 inline" />
                  Generate
                </Button>
                <Button onClick={() => setViewMode('edit')} variant="secondary">
                  <Edit2 className="w-4 h-4 mr-2 inline" />
                  Edit
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex gap-2">
              <Button onClick={handleAddSchedule} variant="secondary">
                <Plus className="w-4 h-4 mr-2 inline" />
                Add Shift
              </Button>
              <Button onClick={handleConfirmChanges} variant="primary">
                <Check className="w-4 h-4 mr-2 inline" />
                Confirm & Save
              </Button>
              <Button
                onClick={() => {
                  setViewMode('view');
                  setEditedSchedules(JSON.parse(JSON.stringify(schedules)));
                }}
                variant="ghost"
              >
                <X className="w-4 h-4 mr-2 inline" />
                Cancel
              </Button>
            </div>
          )
        }
      >
        {loading ? (
          <div className="p-12 text-center text-gray-500">Loading schedules...</div>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-max">
              {/* Header with days */}
              <div className="grid gap-0 border border-gray-300 rounded-lg overflow-hidden" style={{ gridTemplateColumns: '250px repeat(7, 1fr)' }}>
                <div className="bg-gray-900 text-white p-4 font-bold">Employee / Role</div>
                {weekDates.map((date, idx) => {
                  const d = new Date(date);
                  const dayNum = d.getDate();
                  return (
                    <div key={date} className="bg-gray-100 p-3 border-l border-gray-300 font-bold text-sm text-center">
                      <div className="text-gray-600">{dayNames[idx]}</div>
                      <div className="text-lg text-gray-900">{dayNum}</div>
                    </div>
                  );
                })}

                {/* Employee rows */}
                {employees.map((emp) => (
                  <React.Fragment key={emp.id}>
                    <div className="bg-white border-b border-t border-gray-300 p-3 font-semibold text-sm flex flex-col justify-center sticky left-0 z-10 bg-gray-50">
                      <div className="text-gray-900">{emp.first_name} {emp.last_name}</div>
                      {emp.role_id && (
                        <div className={`text-xs mt-1 px-2 py-1 rounded w-fit ${getRoleColor(emp.role_id)}`}>
                          {getRoleName(emp.role_id)}
                        </div>
                      )}
                    </div>

                    {weekDates.map((date) => {
                      const daySchedules = displaySchedules.filter(
                        s => s.employee_id === emp.id && s.date === date
                      );
                      const onLeave = isOnLeave(emp.id, date);

                      return (
                        <div
                          key={`${emp.id}-${date}`}
                          className={`border-b border-l border-gray-300 p-2 min-h-[120px] relative transition ${
                            onLeave ? 'bg-red-50' : 'bg-white hover:bg-gray-50'
                          }`}
                          onDragOver={(e) => viewMode === 'edit' && !onLeave && e.preventDefault()}
                          onDrop={(e) => {
                            if (viewMode === 'edit' && draggedSchedule && !onLeave) {
                              setEditedSchedules(editedSchedules.map(s =>
                                s.id === draggedSchedule.id
                                  ? { ...s, employee_id: emp.id, date }
                                  : s
                              ));
                              setDraggedSchedule(null);
                            }
                          }}
                        >
                          {onLeave && (
                            <div className="text-center py-6">
                              <div className="font-bold text-red-700 text-sm">LEAVE</div>
                              <div className="text-xs text-red-600 mt-1">Approved Time Off</div>
                            </div>
                          )}
                          {!onLeave && daySchedules.map((sched) => (
                            <div
                              key={sched.id}
                              draggable={viewMode === 'edit'}
                              onDragStart={() => viewMode === 'edit' && setDraggedSchedule(sched)}
                              onDragEnd={() => setDraggedSchedule(null)}
                              onClick={() => viewMode === 'view' && (setSelectedSchedule(sched), setShowDetailModal(true))}
                              className={`
                                p-2 rounded mb-1 text-xs font-semibold cursor-pointer
                                transition-all border-l-4
                                ${getRoleColor(sched.role_id)}
                                ${viewMode === 'edit' ? 'cursor-move hover:shadow-lg' : 'hover:shadow-md'}
                              `}
                              style={{ borderLeftColor: '#1e40af' }}
                            >
                              {editingScheduleId === sched.id ? (
                                <div className="space-y-1">
                                  <input
                                    type="time"
                                    value={editingTimes.start_time}
                                    onChange={(e) => setEditingTimes({ ...editingTimes, start_time: e.target.value })}
                                    className="w-full px-1 py-0.5 border rounded text-xs"
                                  />
                                  <input
                                    type="time"
                                    value={editingTimes.end_time}
                                    onChange={(e) => setEditingTimes({ ...editingTimes, end_time: e.target.value })}
                                    className="w-full px-1 py-0.5 border rounded text-xs"
                                  />
                                  <div className="flex gap-1">
                                    <button
                                      onClick={handleSaveTimes}
                                      className="flex-1 bg-green-500 text-white px-1 py-0.5 rounded text-xs hover:bg-green-600"
                                    >
                                      Save
                                    </button>
                                    <button
                                      onClick={() => {
                                        setEditingScheduleId(null);
                                        setEditingTimes(null);
                                      }}
                                      className="flex-1 bg-gray-400 text-white px-1 py-0.5 rounded text-xs hover:bg-gray-500"
                                    >
                                      Cancel
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <div>
                                  <div className="font-bold">{sched.start_time} - {sched.end_time}</div>
                                  <div className="text-xs opacity-75 mt-0.5">{getRoleName(sched.role_id)}</div>
                                  {viewMode === 'edit' && (
                                    <div className="flex gap-1 mt-1">
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleEditTimes(sched);
                                        }}
                                        className="text-blue-600 hover:text-blue-800"
                                        title="Edit times"
                                      >
                                        <Clock className="w-3 h-3" />
                                      </button>
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          handleDeleteScheduleEdit(sched.id);
                                        }}
                                        className="text-red-600 hover:text-red-800"
                                        title="Delete shift"
                                      >
                                        <Trash2 className="w-3 h-3" />
                                      </button>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      );
                    })}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Week Picker Modal */}
      <Modal
        isOpen={showWeekPicker}
        onClose={() => setShowWeekPicker(false)}
        title="Generate Schedule"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Week to Generate
            </label>
            <input
              type="date"
              value={selectedWeek}
              onChange={(e) => setSelectedWeek(getMonday(new Date(e.target.value)))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
            <p className="text-xs text-gray-500 mt-2">
              Week: {getWeekDates(selectedWeek)[0]} to {getWeekDates(selectedWeek)[6]}
            </p>
          </div>
          <div className="flex gap-2 justify-end">
            <Button onClick={() => setShowWeekPicker(false)} variant="ghost">
              Cancel
            </Button>
            <Button onClick={handleGenerateSchedule} variant="primary" disabled={loading}>
              {loading ? 'Generating...' : 'Generate'}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Detail Modal */}
      <Modal
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        title="Schedule Details"
      >
        {selectedSchedule && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-600">Employee</label>
                <p className="font-semibold">{getEmployeeName(selectedSchedule.employee_id)}</p>
              </div>
              <div>
                <label className="text-sm text-gray-600">Role</label>
                <p className="font-semibold">{getRoleName(selectedSchedule.role_id)}</p>
              </div>
              <div>
                <label className="text-sm text-gray-600">Date</label>
                <p className="font-semibold">{selectedSchedule.date}</p>
              </div>
              <div>
                <label className="text-sm text-gray-600">Time</label>
                <p className="font-semibold">{selectedSchedule.start_time} - {selectedSchedule.end_time}</p>
              </div>
              <div className="col-span-2">
                <label className="text-sm text-gray-600">Status</label>
                <p className="font-semibold capitalize">{selectedSchedule.status}</p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button onClick={() => setShowDetailModal(false)} variant="primary">
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ScheduleManager;
