import React, { useState, useEffect } from 'react';
import { Clock, Check, X, AlertCircle, Download, CalendarDays } from 'lucide-react';
import Card from './common/Card';
import Button from './common/Button';
import Table from './common/Table';
import { recordAttendance, getAttendanceSummary, getWeeklyAttendance } from '../services/api';

const AttendanceTracker = ({ employees = [], schedules = [] }) => {
  const [attendance, setAttendance] = useState([]);
  const [loading, setLoading] = useState(false);
  const [weekStart, setWeekStart] = useState(
    new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [weekEnd, setWeekEnd] = useState(new Date().toISOString().split('T')[0]);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    loadAttendanceData();
  }, [weekStart, weekEnd]);

  const loadAttendanceData = async () => {
    setLoading(true);
    try {
      const response = await getAttendanceSummary(weekStart, weekEnd);
      setSummary(response.data);
      
      // If employee selected, get their detailed attendance
      if (selectedEmployee) {
        const empResponse = await getWeeklyAttendance(selectedEmployee, weekStart);
        setAttendance(empResponse.data.records || []);
      }
    } catch (error) {
      console.error('Failed to load attendance:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'onTime':
        return 'bg-green-100 text-green-800';
      case 'slightlyLate':
        return 'bg-yellow-100 text-yellow-800';
      case 'late':
      case 'veryLate':
        return 'bg-red-100 text-red-800';
      case 'missed':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const summaryColumns = [
    {
      header: 'Employee',
      accessor: 'employee_name'
    },
    {
      header: 'Days Worked',
      accessor: 'days_worked'
    },
    {
      header: 'Total Hours',
      accessor: row => `${row.total_worked_hours}h`
    },
    {
      header: 'Overtime',
      accessor: row => `${row.total_overtime}h`
    },
    {
      header: 'On-Time %',
      accessor: row => (
        <span className={`px-2 py-1 rounded text-sm ${
          row.on_time_percentage >= 80 ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
        }`}>
          {row.on_time_percentage}%
        </span>
      )
    },
    {
      header: 'Late Count',
      accessor: 'late_count'
    }
  ];

  const recordColumns = [
    { header: 'Date', accessor: 'date' },
    { header: 'In Time', accessor: 'in_time' },
    { header: 'Out Time', accessor: 'out_time' },
    {
      header: 'Status',
      accessor: row => (
        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(row.status)}`}>
          {row.status}
        </span>
      )
    },
    {
      header: 'Worked',
      accessor: row => `${row.worked_hours}h`
    },
    {
      header: 'Overtime',
      accessor: row => row.overtime_hours > 0 ? `${row.overtime_hours}h` : '-'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-4">
            <Clock size={24} className="text-blue-600" />
            <h2 className="text-2xl font-bold">Attendance Management</h2>
          </div>
        </div>

        {/* Date range and filters */}
        <div className="flex gap-4 items-end flex-wrap">
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
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Employee</label>
            <select
              value={selectedEmployee || ''}
              onChange={(e) => setSelectedEmployee(e.target.value ? parseInt(e.target.value) : null)}
              className="border border-gray-300 rounded-md shadow-sm p-2"
            >
              <option value="">All Employees</option>
              {employees.map(emp => (
                <option key={emp.id} value={emp.id}>
                  {emp.first_name} {emp.last_name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </Card>

      {/* Department Summary */}
      {summary && !selectedEmployee && (
        <div>
          <h3 className="text-xl font-bold mb-4">Department Attendance Summary</h3>
          <Card>
            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : summary.summary.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <AlertCircle className="inline mb-2 text-gray-400" size={40} />
                <p>No attendance records found</p>
              </div>
            ) : (
              <Table
                data={summary.summary}
                columns={summaryColumns}
                striped
              />
            )}
          </Card>
        </div>
      )}

      {/* Individual Employee Attendance */}
      {selectedEmployee && (
        <div>
          <h3 className="text-xl font-bold mb-4">
            {employees.find(e => e.id === selectedEmployee)?.first_name} {employees.find(e => e.id === selectedEmployee)?.last_name} - Weekly Attendance
          </h3>
          <Card>
            {loading ? (
              <div className="text-center py-8 text-gray-500">Loading...</div>
            ) : attendance.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CalendarDays className="inline mb-2 text-gray-400" size={40} />
                <p>No attendance records found</p>
              </div>
            ) : (
              <Table
                data={attendance}
                columns={recordColumns}
                striped
              />
            )}
          </Card>

          {/* Weekly Stats */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4">
              <Card>
                <div className="text-center">
                  <p className="text-gray-600 text-sm mb-2">Total Worked</p>
                  <p className="text-3xl font-bold text-blue-600">
                    {summary.summary[0]?.total_worked_hours || 0}h
                  </p>
                </div>
              </Card>
              <Card>
                <div className="text-center">
                  <p className="text-gray-600 text-sm mb-2">Overtime</p>
                  <p className="text-3xl font-bold text-red-600">
                    {summary.summary[0]?.total_overtime || 0}h
                  </p>
                </div>
              </Card>
              <Card>
                <div className="text-center">
                  <p className="text-gray-600 text-sm mb-2">On-Time</p>
                  <p className="text-3xl font-bold text-green-600">
                    {summary.summary[0]?.on_time_percentage || 0}%
                  </p>
                </div>
              </Card>
              <Card>
                <div className="text-center">
                  <p className="text-gray-600 text-sm mb-2">Days Worked</p>
                  <p className="text-3xl font-bold text-purple-600">
                    {summary.summary[0]?.days_worked || 0}
                  </p>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Attendance Stats */}
      {summary && !selectedEmployee && summary.summary.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <div className="text-center">
              <p className="text-gray-600 text-sm mb-2">Avg. Hours/Employee</p>
              <p className="text-3xl font-bold text-blue-600">
                {(summary.summary.reduce((acc, e) => acc + e.total_worked_hours, 0) / summary.summary.length).toFixed(1)}h
              </p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <p className="text-gray-600 text-sm mb-2">Avg. On-Time %</p>
              <p className="text-3xl font-bold text-green-600">
                {(summary.summary.reduce((acc, e) => acc + e.on_time_percentage, 0) / summary.summary.length).toFixed(1)}%
              </p>
            </div>
          </Card>
          <Card>
            <div className="text-center">
              <p className="text-gray-600 text-sm mb-2">Total Overtime</p>
              <p className="text-3xl font-bold text-red-600">
                {summary.summary.reduce((acc, e) => acc + e.total_overtime, 0).toFixed(1)}h
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
};

export default AttendanceTracker;
