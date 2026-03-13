// src/components/analytics/MacroPieChart.jsx
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { useTheme } from '../../store/ThemeContext';

const COLORS = ['#3b82f6', '#f97316', '#a855f7'];

const MacroPieChart = ({ logs }) => {
  const { dark } = useTheme();

  const tooltipBg     = dark ? '#1c1c1c'  : '#ffffff';
  const tooltipBorder = dark ? '#ffffff15' : '#e5e7eb';
  const legendColor   = dark ? '#6b7280'  : '#6b7280';

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    return (
      <div style={{ background: tooltipBg, border: `1px solid ${tooltipBorder}` }}
        className="rounded-xl shadow-lg px-3 py-2 text-xs"
      >
        <p className="font-semibold" style={{ color: payload[0].payload.fill }}>
          {payload[0].name}
        </p>
        <p className={dark ? 'text-gray-400' : 'text-gray-600'}>{payload[0].value}g</p>
      </div>
    );
  };

  if (!logs || logs.length === 0) {
    return (
      <div className={`flex items-center justify-center h-48 text-sm ${dark ? 'text-gray-600' : 'text-gray-400'}`}>
        No data yet
      </div>
    );
  }

  const protein = logs.reduce((s, l) => s + (l.protein_g || 0), 0);
  const carbs   = logs.reduce((s, l) => s + (l.carbs_g   || 0), 0);
  const fat     = logs.reduce((s, l) => s + (l.fat_g     || 0), 0);

  const data = [
    { name: 'Protein', value: Math.round(protein) },
    { name: 'Carbs',   value: Math.round(carbs)   },
    { name: 'Fat',     value: Math.round(fat)      },
  ].filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div className={`flex items-center justify-center h-48 text-sm ${dark ? 'text-gray-600' : 'text-gray-400'}`}>
        No macro data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(v) => <span style={{ color: legendColor, fontSize: 12 }}>{v}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default MacroPieChart;