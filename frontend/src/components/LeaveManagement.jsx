import React, { useState, useEffect } from 'react';
import { Calendar, Plus, Trash2, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import api from '../services/api';

const LeaveManagement = ({ currentUser, departmentId }) => {
  const [leaves, setLeaves] = useState([]);
  const [unavailability, setUnavailability] = useState([]);
  const [showLeaveForm, setShowLeaveForm] = useState(false);
  const [showUnavailForm, setShowUnavailForm] = useState(false);
  const [employees, setEmployees] = useState([]);
  const [activeTab, setActiveTab] = useState('leaves');
  const [loading, setLoading] = useState(false);

  const [leaveForm, setLeaveForm] = useState({
    employee_id: '',
    start_date: '',
    end_date: '',
    leave_type: 'vacation',
    reason: ''
  });

  const [unavailForm, setUnavailForm] = useState({
    employee_id: '',
    date: '',
    reason: ''
  });

  const leaveTypes = [
    { value: 'vacation', label: 'Vacation' },
    { value: 'sick', label: 'Sick Leave' },
    { value: 'personal', label: 'Personal' },
    { value: 'training', label: 'Training' },
    { value: 'other', label: 'Other' }
  ];

  const unavailReasons = [
    'Sick',
    'Personal',
    'Training',
    'Maintenance',
    'Meeting',
    'Appointment',
    'Other'
  ];

  useEffect(() => {
    loadData();
  }, [departmentId]);

  const loadData = async () => {
    setLoading(true);
    try {
      // Load employees for dropdown
      const empRes = await api.get('/employees');
      setEmployees(empRes.data);

      // Load leaves
      const leavesRes = await api.get('/leave-requests');
      setLeaves(leavesRes.data);

      // Load unavailability
      const unavailRes = await api.get('/unavailability');
      setUnavailability(unavailRes.data);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddLeave = async () => {
    if (!leaveForm.employee_id || !leaveForm.start_date || !leaveForm.end_date) {
      alert('Please fill all required fields');
      return;
    }

    try {
      await api.post('/leave-requests', leaveForm);
      setLeaveForm({ employee_id: '', start_date: '', end_date: '', leave_type: 'vacation', reason: '' });
      setShowLeaveForm(false);
      await loadData();
    } catch (error) {
      console.error('Error creating leave request:', error);
      alert('Failed to create leave request');
    }
  };

  const handleAddUnavailability = async () => {
    if (!unavailForm.employee_id || !unavailForm.date) {
      alert('Please fill all required fields');
      return;
    }

    try {
      await api.post('/unavailability', unavailForm);
      setUnavailForm({ employee_id: '', date: '', reason: '' });
      setShowUnavailForm(false);
      await loadData();
    } catch (error) {
      console.error('Error creating unavailability:', error);
      alert('Failed to mark unavailability');
    }
  };

  const handleDeleteUnavailability = async (id) => {
    if (!window.confirm('Delete this unavailability record?')) return;

    try {
      await api.delete(`/unavailability/${id}`);
      await loadData();
    } catch (error) {
      console.error('Error deleting unavailability:', error);
      alert('Failed to delete record');
    }
  };

  const handleApproveLeave = async (leaveId) => {
    try {
      await api.put(`/leave-requests/${leaveId}/approve`, { review_notes: 'Approved' });
      await loadData();
    } catch (error) {
      console.error('Error approving leave:', error);
      alert('Failed to approve leave');
    }
  };

  const handleRejectLeave = async (leaveId) => {
    try {
      await api.put(`/leave-requests/${leaveId}/reject`, { review_notes: 'Rejected' });
      await loadData();
    } catch (error) {
      console.error('Error rejecting leave:', error);
      alert('Failed to reject leave');
    }
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
      approved: { bg: 'bg-green-100', text: 'text-green-800', label: 'Approved' },
      rejected: { bg: 'bg-red-100', text: 'text-red-800', label: 'Rejected' }
    };
    const config = statusMap[status] || statusMap.pending;
    return <span className={`px-2 py-1 rounded text-sm ${config.bg} ${config.text}`}>{config.label}</span>;
  };

  const getEmployeeName = (empId) => {
    const emp = employees.find(e => e.id === parseInt(empId));
    return emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('leaves')}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === 'leaves'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          <Calendar className="inline mr-2 w-4 h-4" />
          Leave Requests
        </button>
        <button
          onClick={() => setActiveTab('unavail')}
          className={`px-4 py-2 font-medium border-b-2 transition ${
            activeTab === 'unavail'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900'
          }`}
        >
          <AlertCircle className="inline mr-2 w-4 h-4" />
          Unavailability
        </button>
      </div>

      {/* Leave Requests Tab */}
      {activeTab === 'leaves' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Leave Requests</h3>
            {currentUser?.user_type === 'manager' && (
              <button
                onClick={() => setShowLeaveForm(!showLeaveForm)}
                className="flex items-center gap-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                <Plus className="w-4 h-4" />
                New Leave Request
              </button>
            )}
          </div>

          {/* Leave Form */}
          {showLeaveForm && currentUser?.user_type === 'manager' && (
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Employee</label>
                  <select
                    value={leaveForm.employee_id}
                    onChange={(e) => setLeaveForm({ ...leaveForm, employee_id: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">Select employee...</option>
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>
                        {emp.first_name} {emp.last_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Leave Type</label>
                  <select
                    value={leaveForm.leave_type}
                    onChange={(e) => setLeaveForm({ ...leaveForm, leave_type: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  >
                    {leaveTypes.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Start Date</label>
                  <input
                    type="date"
                    value={leaveForm.start_date}
                    onChange={(e) => setLeaveForm({ ...leaveForm, start_date: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">End Date</label>
                  <input
                    type="date"
                    value={leaveForm.end_date}
                    onChange={(e) => setLeaveForm({ ...leaveForm, end_date: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-1">Reason</label>
                  <textarea
                    value={leaveForm.reason}
                    onChange={(e) => setLeaveForm({ ...leaveForm, reason: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                    rows="2"
                    placeholder="Optional reason for leave..."
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleAddLeave}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                >
                  Submit Leave Request
                </button>
                <button
                  onClick={() => setShowLeaveForm(false)}
                  className="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Leaves List */}
          <div className="space-y-3">
            {leaves.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No leave requests found</p>
            ) : (
              leaves.map(leave => (
                <div key={leave.id} className="border rounded-lg p-4 bg-white hover:shadow-md transition">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-semibold">{getEmployeeName(leave.employee_id)}</h4>
                      <p className="text-sm text-gray-600">
                        {formatDate(leave.start_date)} to {formatDate(leave.end_date)}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        <span className="font-medium">Type:</span> {leave.leave_type}
                      </p>
                      {leave.reason && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">Reason:</span> {leave.reason}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      {getStatusBadge(leave.status)}
                      {leave.status === 'pending' && currentUser?.user_type === 'manager' && (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleApproveLeave(leave.id)}
                            className="flex items-center gap-1 bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600"
                          >
                            <CheckCircle className="w-3 h-3" />
                            Approve
                          </button>
                          <button
                            onClick={() => handleRejectLeave(leave.id)}
                            className="flex items-center gap-1 bg-red-500 text-white px-3 py-1 rounded text-sm hover:bg-red-600"
                          >
                            <Trash2 className="w-3 h-3" />
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Unavailability Tab */}
      {activeTab === 'unavail' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">Employee Unavailability</h3>
            {currentUser?.user_type === 'manager' && (
              <button
                onClick={() => setShowUnavailForm(!showUnavailForm)}
                className="flex items-center gap-2 bg-orange-500 text-white px-4 py-2 rounded hover:bg-orange-600"
              >
                <Plus className="w-4 h-4" />
                Mark Unavailable
              </button>
            )}
          </div>

          {/* Unavailability Form */}
          {showUnavailForm && currentUser?.user_type === 'manager' && (
            <div className="bg-orange-50 p-4 rounded-lg border border-orange-200 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Employee</label>
                  <select
                    value={unavailForm.employee_id}
                    onChange={(e) => setUnavailForm({ ...unavailForm, employee_id: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">Select employee...</option>
                    {employees.map(emp => (
                      <option key={emp.id} value={emp.id}>
                        {emp.first_name} {emp.last_name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Date</label>
                  <input
                    type="date"
                    value={unavailForm.date}
                    onChange={(e) => setUnavailForm({ ...unavailForm, date: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-1">Reason</label>
                  <select
                    value={unavailForm.reason}
                    onChange={(e) => setUnavailForm({ ...unavailForm, reason: e.target.value })}
                    className="w-full border rounded px-3 py-2"
                  >
                    <option value="">Select reason...</option>
                    {unavailReasons.map(reason => (
                      <option key={reason} value={reason}>{reason}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={handleAddUnavailability}
                  className="bg-orange-500 text-white px-4 py-2 rounded hover:bg-orange-600"
                >
                  Mark Unavailable
                </button>
                <button
                  onClick={() => setShowUnavailForm(false)}
                  className="bg-gray-300 text-gray-700 px-4 py-2 rounded hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Unavailability List */}
          <div className="space-y-3">
            {unavailability.length === 0 ? (
              <p className="text-gray-500 text-center py-4">No unavailability records found</p>
            ) : (
              unavailability.map(record => (
                <div key={record.id} className="border rounded-lg p-4 bg-white hover:shadow-md transition">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <h4 className="font-semibold">{getEmployeeName(record.employee_id)}</h4>
                      <p className="text-sm text-gray-600">
                        <Calendar className="inline mr-2 w-4 h-4" />
                        {formatDate(record.date)}
                      </p>
                      {record.reason && (
                        <p className="text-sm text-gray-600 mt-1">
                          <span className="font-medium">Reason:</span> {record.reason}
                        </p>
                      )}
                    </div>
                    {currentUser?.user_type === 'manager' && (
                      <button
                        onClick={() => handleDeleteUnavailability(record.id)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default LeaveManagement;
