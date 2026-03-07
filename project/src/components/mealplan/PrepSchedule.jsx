// src/components/mealplan/PrepSchedule.jsx

import { CalendarClock, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getPrepSchedule } from '../../api/mealPlans';

const PrepSchedule = ({ planId }) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['prep', planId],
    queryFn: () => getPrepSchedule(planId),
    enabled: !!planId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40">
        <Loader2 className="animate-spin text-primary-600" size={24} />
      </div>
    );
  }

  if (isError) {
    return (
      <p className="text-sm text-red-500 text-center py-8">
        Failed to load prep schedule.
      </p>
    );
  }

  const sessions = data?.prep_sessions || data?.sessions || [];
  const tips = data?.tips || data?.general_tips || [];

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <CalendarClock size={18} className="text-primary-600" />
        <h3 className="text-base font-semibold text-gray-900">Prep Schedule</h3>
      </div>

      {sessions.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">No prep sessions found.</p>
      ) : (
        sessions.map((session, i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-gray-800">
                {session.session_name || session.day || `Session ${i + 1}`}
              </h4>
              {session.total_time_minutes && (
                <span className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full">
                  ~{session.total_time_minutes} min
                </span>
              )}
            </div>
            <ul className="space-y-1.5">
              {(session.tasks || session.items || []).map((task, j) => (
                <li key={j} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-primary-500 mt-0.5">•</span>
                  <span>{typeof task === 'string' ? task : task.task || task.description || JSON.stringify(task)}</span>
                </li>
              ))}
            </ul>
          </div>
        ))
      )}

      {tips.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-amber-600 mb-2">💡 Tips</p>
          <ul className="space-y-1">
            {tips.map((tip, i) => (
              <li key={i} className="text-sm text-amber-800">• {tip}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default PrepSchedule;