import React, { useState } from 'react';
import { AlertCircle, Sparkles, Calendar } from 'lucide-react';
import Button from './common/Button';
import Modal from './common/Modal';
import { generateSchedules } from '../services/api';
import { format, addDays, startOfWeek } from 'date-fns';

const ScheduleGenerator = ({ onSuccess, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState([]);
  const [startDate, setStartDate] = useState(format(startOfWeek(new Date(), { weekStartsOn: 1 }), 'yyyy-MM-dd'));
  const [endDate, setEndDate] = useState(format(addDays(new Date(), 6), 'yyyy-MM-dd'));
  const [generatedSchedules, setGeneratedSchedules] = useState(null);

  const handleGenerate = async () => {
    if (!startDate || !endDate) {
      setError('Please select both start and end dates');
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError('Start date must be before end date');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setFeedback([]);

      const response = await generateSchedules(startDate, endDate);
      const data = response.data;

      setFeedback(data.feedback || []);
      setGeneratedSchedules(data);

      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate schedule');
      console.error('Schedule generation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'success': return 'bg-green-50 border-green-200 text-green-700';
      case 'error': return 'bg-red-50 border-red-200 text-red-700';
      case 'warning': return 'bg-yellow-50 border-yellow-200 text-yellow-700';
      default: return 'bg-blue-50 border-blue-200 text-blue-700';
    }
  };

  if (generatedSchedules && generatedSchedules.success) {
    return (
      <Modal isOpen={true} onClose={onClose} title="Schedule Generation Complete">
        <div className="space-y-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="text-green-600 flex-shrink-0 mt-0.5" size={20} />
              <div>
                <h3 className="font-semibold text-green-800">✅ Schedule Generated Successfully</h3>
                <p className="text-green-700 text-sm mt-1">
                  {generatedSchedules.schedules_created} shift assignments created
                </p>
              </div>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Generation Details:</h4>
            <div className="space-y-2 text-sm">
              <p className="text-gray-700">
                <span className="font-medium">Period:</span> {generatedSchedules.start_date} to {generatedSchedules.end_date}
              </p>
              <p className="text-gray-700">
                <span className="font-medium">Shifts Created:</span> {generatedSchedules.schedules_created}
              </p>
            </div>
          </div>

          {feedback.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Algorithm Feedback:</h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {feedback.map((msg, idx) => (
                  <div key={idx} className={`rounded-lg p-3 border ${getSeverityColor(msg.severity)}`}>
                    <p className="text-sm">{msg.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 justify-end pt-4 border-t">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal isOpen={true} onClose={onClose} title="Generate Schedule">
      <div className="space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="text-red-600 flex-shrink-0 mt-0.5" size={20} />
              <div>
                <h3 className="font-semibold text-red-800">Error</h3>
                <p className="text-red-700 text-sm mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex gap-3">
            <Sparkles className="text-blue-600 flex-shrink-0 mt-0.5" size={20} />
            <div className="text-sm text-blue-700">
              <p className="font-medium mb-1">Priority-Based Distribution</p>
              <p className="text-xs">This algorithm uses Google OR-Tools to generate optimal schedules considering role priorities, employee availability, and constraints.</p>
            </div>
          </div>
        </div>

        {feedback.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Generation Progress:</h4>
            <div className="space-y-2 max-h-48 overflow-y-auto bg-gray-50 rounded-lg p-3">
              {feedback.map((msg, idx) => (
                <div key={idx} className={`text-xs p-2 rounded ${getSeverityColor(msg.severity)}`}>
                  {msg.message}
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3 justify-end pt-4 border-t">
          <Button variant="secondary" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button 
            onClick={handleGenerate}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <Sparkles size={18} />
            {loading ? 'Generating...' : 'Generate Schedule'}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default ScheduleGenerator;
