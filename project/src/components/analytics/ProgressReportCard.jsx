// src/components/analytics/ProgressReportCard.jsx

import { TrendingUp, Lightbulb, Star, AlertTriangle } from 'lucide-react';

const ProgressReportCard = ({ report }) => {
  if (!report) return null;

  return (
    <div className="space-y-4">

      {/* Overview */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Avg Adherence', value: `${report.avg_adherence_pct?.toFixed(0) ?? '—'}%`,  color: 'text-primary-600' },
          { label: 'Best Day',      value: report.best_day  || '—',                             color: 'text-green-600'   },
          { label: 'Worst Day',     value: report.worst_day || '—',                             color: 'text-red-500'     },
          { label: 'Goal Status',   value: report.goal_progress || '—',                         color: 'text-blue-600'    },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-gray-50 rounded-xl p-3 text-center">
            <p className={`text-base font-bold ${color} leading-tight`}>{value}</p>
            <p className="text-xs text-gray-400 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Patterns */}
      {report.patterns_identified?.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={15} className="text-blue-500" />
            <h4 className="text-sm font-semibold text-gray-900">Patterns Identified</h4>
          </div>
          <ul className="space-y-2">
            {report.patterns_identified.map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-blue-400 mt-0.5 flex-shrink-0">•</span>
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations?.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb size={15} className="text-amber-500" />
            <h4 className="text-sm font-semibold text-gray-900">Recommendations</h4>
          </div>
          <ul className="space-y-2">
            {report.recommendations.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-amber-400 mt-0.5 flex-shrink-0">→</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Motivational note */}
      {report.motivational_note && (
        <div className="bg-primary-50 border border-primary-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-1">
            <Star size={15} className="text-primary-600" />
            <h4 className="text-sm font-semibold text-primary-800">AI Coach says</h4>
          </div>
          <p className="text-sm text-primary-700 leading-relaxed">{report.motivational_note}</p>
        </div>
      )}
    </div>
  );
};

export default ProgressReportCard;