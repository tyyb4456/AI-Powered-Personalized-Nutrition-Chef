// src/components/analytics/AdherenceChart.jsx
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts';
import { useTheme } from '../../store/ThemeContext';

const AdherenceChart = ({ logs }) => {
  const { dark } = useTheme();

  const tickColor    = dark ? '#4b5563' : '#9ca3af'; // gray-600 / gray-400
  const gridColor    = dark ? '#ffffff10' : '#f3f4f6';
  const tooltipBg    = dark ? '#1c1c1c'  : '#ffffff';
  const tooltipBorder = dark ? '#ffffff15' : '#e5e7eb';

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <div style={{ background: tooltipBg, border: `1px solid ${tooltipBorder}` }}
        className="rounded-xl shadow-lg px-4 py-3 text-xs"
      >
        <p className={`font-semibold mb-1 ${dark ? 'text-white' : 'text-gray-800'}`}>{label}</p>
        <p className="text-amber-400">Actual: <strong>{d?.actual} kcal</strong></p>
        <p className={dark ? 'text-gray-500' : 'text-gray-400'}>Target: {d?.planned} kcal</p>
        <p className={dark ? 'text-blue-400' : 'text-blue-500'}>Adherence: {d?.pct?.toFixed(0)}%</p>
      </div>
    );
  };

  if (!logs || logs.length === 0) {
    return (
      <div className={`flex items-center justify-center h-48 text-sm ${dark ? 'text-gray-600' : 'text-gray-400'}`}>
        No data yet — log some meals first
      </div>
    );
  }

  const data = logs.map((log) => ({
    day:     log.log_date?.slice(5) || log.log_date,
    actual:  log.actual_calories  || 0,
    planned: log.planned_calories || 0,
    pct:     log.adherence_pct    || 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="day" tick={{ fontSize: 11, fill: tickColor }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: tickColor }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' }} />
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
                entry.pct >= 90
                  ? '#619175'   // soft green
                  : entry.pct >= 60
                  ? '#fcd34d'   // soft amber
                  : '#fca5a5'   // soft red
              }
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default AdherenceChart;