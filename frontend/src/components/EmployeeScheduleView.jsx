import React, { useState, useEffect } from 'react';
import { Calendar, Clock, CheckCircle, AlertCircle } from 'lucide-react';
import Card from './common/Card';
import Button from './common/Button';
import Modal from './common/Modal';
import { getSchedules, recordAttendance } from '../services/api';

const EmployeeScheduleView = ({ employeeId }) => {
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [weekStart, setWeekStart] = useState(
    new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [weekEnd, setWeekEnd] = useState(
    new Date(Date.now() + 4 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [showCheckInModal, setShowCheckInModal] = useState(false);
  const [selectedSchedule, setSelectedSchedule] = useState(null);
  const [checkInTime, setCheckInTime] = useState('');

  useEffect(() => {
    loadSchedules();
  }, [weekStart, weekEnd]);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      const response = await getSchedules(weekStart, weekEnd);
      const filteredSchedules = response.data.filter(s => s.employee_id === employeeId);
      setSchedules(filteredSchedules);
    } catch (error) {
      console.error('Failed to load schedules:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIn = async () => {
    if (!checkInTime) {
      alert('Please enter check-in time');
      return;
    }

    try {
      await recordAttendance({
        schedule_id: selectedSchedule.id,
        in_time: checkInTime,
        status: 'pending'
      });
      alert('✅ Check-in recorded successfully');
      setShowCheckInModal(false);
      setCheckInTime('');
      loadSchedules();
    } catch (error) {
      alert('Error recording check-in: ' + error.message);
    }
  };

  const getTodaysSchedule = () => {
    const today = new Date().toISOString().split('T')[0];
    return schedules.find(s => s.date === today);
  };

  const getUpcomingSchedules = () => {
    const today = new Date();
    return schedules.filter(s => new Date(s.date) >= today).slice(1, 8);
  };

  const getStatusColor = (schedule) => {
    if (!schedule.status) return 'bg-gray-100 text-gray-800';
    
    switch (schedule.status) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'missed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const todaysSchedule = getTodaysSchedule();
  const upcomingSchedules = getUpcomingSchedules();

  return (
    <div className="space-y-6">
      {/* Check-In Modal */}
      <Modal isOpen={showCheckInModal} onClose={() => setShowCheckInModal(false)}>
        <div className="bg-white rounded-lg shadow-lg p-6 max-w-md">
          <h2 className="text-xl font-bold mb-4">Check In</h2>
          <p className="text-gray-600 mb-4">
            Shift: {selectedSchedule?.start_time} - {selectedSchedule?.end_time}
          </p>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Check-In Time</label>
            <input
              type="time"
              value={checkInTime}
              onChange={(e) => setCheckInTime(e.target.value)}
              className="w-full border border-gray-300 rounded-md shadow-sm p-2"
              defaultValue={new Date().toTimeString().slice(0, 5)}
            />
          </div>
          <div className="flex gap-3 justify-end mt-6">
            <Button onClick={() => setShowCheckInModal(false)} variant="secondary">Cancel</Button>
            <Button onClick={handleCheckIn}>Check In</Button>
          </div>
        </div>
      </Modal>

      {/* Today's Schedule */}
      {todaysSchedule ? (
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-blue-900 mb-2">Today's Shift</h3>
              <div className="space-y-2">
                <p className="text-gray-700">
                  <Clock size={18} className="inline mr-2" />
                  <strong>{todaysSchedule.start_time} - {todaysSchedule.end_time}</strong>
                </p>
                <p className="text-gray-600 text-sm">Role: {todaysSchedule.role_id}</p>
                {todaysSchedule.notes && (
                  <p className="text-gray-600 text-sm">Notes: {todaysSchedule.notes}</p>
                )}
              </div>
            </div>
            <div className="text-right">
              {todaysSchedule.status === 'scheduled' && (
                <Button 
                  onClick={() => {
                    setSelectedSchedule(todaysSchedule);
                    setCheckInTime(new Date().toTimeString().slice(0, 5));
                    setShowCheckInModal(true);
                  }}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle size={18} />
                  Check In
                </Button>
              )}
              {todaysSchedule.status === 'completed' && (
                <div className="text-green-600 font-semibold flex items-center gap-2">
                  <CheckCircle size={20} />
                  Checked In
                </div>
              )}
              <p className={`mt-2 px-3 py-1 rounded text-sm font-medium ${getStatusColor(todaysSchedule)} inline-block`}>
                {todaysSchedule.status}
              </p>
            </div>
          </div>
        </Card>
      ) : (
        <Card className="bg-gray-50 border border-gray-200">
          <div className="flex items-center gap-4 text-gray-600">
            <AlertCircle size={24} className="text-yellow-600" />
            <div>
              <p className="font-semibold">No Shift Today</p>
              <p className="text-sm">You don't have a scheduled shift for today</p>
            </div>
          </div>
        </Card>
      )}

      {/* Date Range Selector */}
      <Card>
        <div className="flex items-center gap-4 mb-4">
          <Calendar size={24} className="text-blue-600" />
          <h3 className="text-lg font-bold">My Schedule</h3>
        </div>
        <div className="flex gap-4 items-end">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">From</label>
            <input
              type="date"
              value={weekStart}
              onChange={(e) => setWeekStart(e.target.value)}
              className="border border-gray-300 rounded-md shadow-sm p-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">To</label>
            <input
              type="date"
              value={weekEnd}
              onChange={(e) => setWeekEnd(e.target.value)}
              className="border border-gray-300 rounded-md shadow-sm p-2"
            />
          </div>
        </div>
      </Card>

      {/* Upcoming Schedules */}
      <div>
        <h3 className="text-lg font-bold mb-4">Upcoming Shifts</h3>
        {loading ? (
          <Card>
            <div className="text-center py-8 text-gray-500">Loading schedules...</div>
          </Card>
        ) : upcomingSchedules.length === 0 ? (
          <Card>
            <div className="text-center py-8 text-gray-500">
              <AlertCircle className="inline mb-2 text-gray-400" size={40} />
              <p>No upcoming shifts scheduled</p>
            </div>
          </Card>
          ) : (
            <div className="space-y-4">
              {upcomingSchedules.map(schedule => (
                <Card key={schedule.id} className="hover:shadow-lg transition-shadow">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-lg text-gray-800">
                        {new Date(schedule.date).toLocaleDateString('en-US', {
                          weekday: 'long',
                          month: 'short',
                          day: 'numeric'
                        })}
                      </p>
                      <p className="text-gray-600 flex items-center gap-2 mt-2">
                        <Clock size={16} />
                        <strong>{schedule.start_time} - {schedule.end_time}</strong>
                      </p>
                      {schedule.notes && (
                        <p className="text-gray-500 text-sm mt-1">Notes: {schedule.notes}</p>
                      )}
                    </div>
                    <div>
                      <span className={`px-4 py-2 rounded-full text-sm font-medium ${getStatusColor(schedule)}`}>
                        {schedule.status}
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
      </div>

      {/* All Schedules */}
      {schedules.length > 0 && (
        <Card>
          <h3 className="text-lg font-bold mb-4">All Schedules ({weekStart} to {weekEnd})</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">Date</th>
                  <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">Time</th>
                  <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">Status</th>
                  <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700">Notes</th>
                </tr>
              </thead>
              <tbody>
                {schedules.map(schedule => (
                  <tr key={schedule.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-800">
                      {new Date(schedule.date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-2 text-gray-800">
                      {schedule.start_time} - {schedule.end_time}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(schedule)}`}>
                        {schedule.status}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-gray-600 text-sm">
                      {schedule.notes || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Schedule Stats */}
      {schedules.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <div className="text-center">
              <p className="text-gray-600 text-sm mb-2">Total Shifts</p>
              <p className="text-3xl font-bold text-blue-600">{schedules.length}</p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <p className="text-gray-600 text-sm mb-2">Days Off</p>
              <p className="text-3xl font-bold text-green-600">
                {7 - new Set(schedules.map(s => s.date)).size}
              </p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <p className="text-gray-600 text-sm mb-2">Total Hours</p>
              <p className="text-3xl font-bold text-purple-600">
                {schedules.reduce((acc, s) => {
                  const start = parseInt(s.start_time.split(':')[0]) * 60 + parseInt(s.start_time.split(':')[1]);
                  const end = parseInt(s.end_time.split(':')[0]) * 60 + parseInt(s.end_time.split(':')[1]);
                  return acc + (end - start) / 60;
                }, 0).toFixed(1)}h
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default EmployeeScheduleView;
