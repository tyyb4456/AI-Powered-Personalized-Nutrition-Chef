// src/components/recipe/MacroBadge.jsx
import { useTheme } from '../../store/ThemeContext';

const DARK_COLORS = {
  calories: 'bg-amber-400/10  text-amber-400  border-amber-400/20',
  protein:  'bg-blue-400/10   text-blue-400   border-blue-400/20',
  carbs:    'bg-orange-400/10 text-orange-400 border-orange-400/20',
  fat:      'bg-purple-400/10 text-purple-400 border-purple-400/20',
  fiber:    'bg-green-400/10  text-green-400  border-green-400/20',
};

const LIGHT_COLORS = {
  calories: 'bg-amber-50  text-amber-700  border-amber-200',
  protein:  'bg-blue-50   text-blue-700   border-blue-200',
  carbs:    'bg-orange-50 text-orange-700 border-orange-200',
  fat:      'bg-purple-50 text-purple-700 border-purple-200',
  fiber:    'bg-green-50  text-green-700  border-green-200',
};

const MacroBadge = ({ label, value, unit, type }) => {
  const { dark } = useTheme();
  const colors = dark ? DARK_COLORS : LIGHT_COLORS;
  const cls = colors[type] || (dark ? 'bg-white/6 text-gray-300 border-white/10' : 'bg-gray-50 text-gray-700 border-gray-200');

  return (
    <div className={`flex flex-col items-center px-3 py-3 rounded-xl border ${cls}`}>
      <span className="text-base font-bold tabular-nums">
        {value}
        <span className="text-xs font-normal ml-0.5 opacity-70">{unit}</span>
      </span>
      <span className="text-xs mt-0.5 opacity-70 font-medium">{label}</span>
    </div>
  );
};

export default MacroBadge;