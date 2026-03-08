// src/components/analytics/MacroPieChart.jsx

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = ['#3b82f6', '#f97316', '#a855f7'];
const LABELS = ['Protein', 'Carbs', 'Fat'];

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm px-3 py-2 text-xs">
      <p className="font-semibold" style={{ color: payload[0].payload.fill }}>
        {payload[0].name}
      </p>
      <p className="text-gray-600">{payload[0].value}g</p>
    </div>
  );
};

const MacroPieChart = ({ logs }) => {
  if (!logs || logs.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-sm text-gray-400">
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
      <div className="flex items-center justify-center h-48 text-sm text-gray-400">
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
          formatter={(v) => <span className="text-xs text-gray-600">{v}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
};

export default MacroPieChart;