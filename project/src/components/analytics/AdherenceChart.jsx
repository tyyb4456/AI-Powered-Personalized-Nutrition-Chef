// src/components/analytics/AdherenceChart.jsx

import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-4 py-3 text-xs">
      <p className="font-semibold text-gray-800 mb-1">{label}</p>
      <p className="text-amber-600">Actual: <strong>{d?.actual} kcal</strong></p>
      <p className="text-gray-400">Target: {d?.planned} kcal</p>
      <p className="text-primary-600">Adherence: {d?.pct?.toFixed(0)}%</p>
    </div>
  );
};

const AdherenceChart = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-gray-400">
        No data yet — log some meals first
      </div>
    );
  }

  const data = logs.map((log) => ({
    day:     log.log_date?.slice(5) || log.log_date,  // MM-DD
    actual:  log.actual_calories  || 0,
    planned: log.planned_calories || 0,
    pct:     log.adherence_pct    || 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
        <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#9ca3af' }} />
        <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={data[0]?.planned || 2000}
          stroke="#16a34a"
          strokeDasharray="4 4"
          label={{ value: 'Target', position: 'right', fontSize: 10, fill: '#16a34a' }}
        />
        <Bar dataKey="actual" radius={[6, 6, 0, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={
                entry.pct >= 90 ? '#22c55e' :
                entry.pct >= 60 ? '#f59e0b' :
                                  '#f87171'
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default AdherenceChart;