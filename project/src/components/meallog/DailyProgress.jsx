// src/components/meallog/DailyProgress.jsx

import { useQuery } from '@tanstack/react-query';
import { getDailyAdherence } from '../../api/mealLogs';
import { Loader2, TrendingUp } from 'lucide-react';

const DailyProgress = ({ date }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['adherence', date],
    queryFn: () => getDailyAdherence(date),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-20">
        <Loader2 className="animate-spin text-primary-600" size={20} />
      </div>
    );
  }

  if (!data) return null;

  const pct     = Math.min(data.adherence_pct || 0, 100);
  const actual  = data.actual_calories  || 0;
  const planned = data.planned_calories || 0;

  const barColor =
    pct >= 90  ? 'bg-green-500'  :
    pct >= 60  ? 'bg-amber-400'  :
                 'bg-red-400';

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={17} className="text-primary-600" />
        <h3 className="text-sm font-semibold text-gray-900">Today's Progress</h3>
      </div>

      <div className="flex items-end justify-between mb-2">
        <span className="text-2xl font-bold text-gray-900">{actual}</span>
        <span className="text-sm text-gray-400">/ {planned} kcal</span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-100 rounded-full h-3 mb-3">
        <div
          className={`h-3 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{pct.toFixed(0)}% of daily target</span>
        <div className="flex gap-3">
          <span>✅ {data.meals_logged} logged</span>
          <span>⏭️ {data.meals_skipped} skipped</span>
        </div>
      </div>
    </div>
  );
};

export default DailyProgress;