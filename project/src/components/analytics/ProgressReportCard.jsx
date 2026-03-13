// src/components/analytics/ProgressReportCard.jsx
import { TrendingUp, Lightbulb, Star } from 'lucide-react';
import { useTheme } from '../../store/ThemeContext';

const ProgressReportCard = ({ report }) => {
  const { dark } = useTheme();
  if (!report) return null;

  const card    = dark ? 'bg-white/4 border-white/8'  : 'bg-white border-black/8';
  const inner   = dark ? 'bg-white/4 border-white/8'  : 'bg-gray-50 border-black/5';
  const text    = dark ? 'text-white'    : 'text-gray-900';
  const muted   = dark ? 'text-gray-500' : 'text-gray-400';
  const subtext = dark ? 'text-gray-300' : 'text-gray-700';
  const divider = dark ? 'border-white/6' : 'border-black/5';
  const bullet  = dark ? 'text-blue-400'  : 'text-blue-500';
  const arrow   = dark ? 'text-amber-400' : 'text-amber-500';

  return (
    <div className="space-y-3">

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Avg Adherence', value: `${report.avg_adherence_pct?.toFixed(0) ?? '—'}%`, color: dark ? 'text-white' : 'text-gray-900' },
          { label: 'Best Day',      value: report.best_day  || '—', color: 'text-green-400' },
          { label: 'Worst Day',     value: report.worst_day || '—', color: 'text-red-400'   },
          { label: 'Goal Status',   value: report.goal_progress || '—', color: dark ? 'text-blue-400' : 'text-blue-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className={`rounded-2xl border p-4 text-center ${card}`}>
            <p className={`text-sm font-bold leading-snug ${color}`}>{value}</p>
            <p className={`text-xs mt-1 ${muted}`}>{label}</p>
          </div>
        ))}
      </div>

      {/* Patterns */}
      {report.patterns_identified?.length > 0 && (
        <div className={`rounded-2xl border p-5 ${card}`}>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={13} className="text-blue-400" />
            <span className={`text-xs font-semibold tracking-widest uppercase ${muted}`}>Patterns Identified</span>
          </div>
          <ul className="space-y-2.5">
            {report.patterns_identified.map((p, i) => (
              <li key={i} className={`flex items-start gap-2.5 text-sm pb-2.5 border-b last:border-0 last:pb-0 ${divider}`}>
                <span className={`shrink-0 mt-0.5 ${bullet}`}>•</span>
                <span className={subtext}>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations?.length > 0 && (
        <div className={`rounded-2xl border p-5 ${card}`}>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb size={13} className="text-amber-400" />
            <span className={`text-xs font-semibold tracking-widest uppercase ${muted}`}>Recommendations</span>
          </div>
          <ul className="space-y-2.5">
            {report.recommendations.map((r, i) => (
              <li key={i} className={`flex items-start gap-2.5 text-sm pb-2.5 border-b last:border-0 last:pb-0 ${divider}`}>
                <span className={`shrink-0 mt-0.5 ${arrow}`}>→</span>
                <span className={subtext}>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Motivational note */}
      {report.motivational_note && (
        <div className={`rounded-2xl border p-5 ${
          dark ? 'bg-amber-400/5 border-amber-400/12' : 'bg-amber-50/80 border-amber-200'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            <Star size={13} className={dark ? 'text-amber-400' : 'text-amber-600'} />
            <span className={`text-xs font-semibold tracking-widest uppercase ${dark ? 'text-amber-400' : 'text-amber-600'}`}>
              AI Coach says
            </span>
          </div>
          <p className={`text-sm leading-relaxed ${dark ? 'text-gray-300' : 'text-amber-900'}`}>
            {report.motivational_note}
          </p>
        </div>
      )}
    </div>
  );
};

export default ProgressReportCard;