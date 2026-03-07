// src/components/meallog/LogEntry.jsx

import { Trash2 } from 'lucide-react';

const SLOT_STYLES = {
  breakfast: 'bg-amber-50  text-amber-700  border-amber-200',
  lunch:     'bg-green-50  text-green-700  border-green-200',
  dinner:    'bg-blue-50   text-blue-700   border-blue-200',
  snack:     'bg-purple-50 text-purple-700 border-purple-200',
};

const SLOT_ICONS = {
  breakfast: '🌅',
  lunch:     '☀️',
  dinner:    '🌙',
  snack:     '🍎',
};

const LogEntry = ({ log, onDelete }) => {
  return (
    <div className="flex items-center justify-between gap-3 bg-white border border-gray-100 rounded-xl px-4 py-3 hover:border-gray-200 transition-colors">

      {/* Left */}
      <div className="flex items-center gap-3 min-w-0">
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border shrink-0 ${SLOT_STYLES[log.meal_slot] || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
          {SLOT_ICONS[log.meal_slot]} {log.meal_slot}
        </span>
        <span className="text-sm font-medium text-gray-800 truncate">{log.dish_name}</span>
      </div>

      {/* Right — macros */}
      <div className="flex items-center gap-4 shrink-0">
        <div className="hidden sm:flex gap-3 text-xs text-gray-500">
          <span className="font-semibold text-amber-600">{log.calories} kcal</span>
          <span>P: {log.protein_g}g</span>
          <span>C: {log.carbs_g}g</span>
          <span>F: {log.fat_g}g</span>
        </div>
        {/* Mobile — calories only */}
        <span className="sm:hidden text-xs font-semibold text-amber-600">{log.calories} kcal</span>

        <button
          onClick={() => onDelete(log.log_id)}
          className="text-gray-300 hover:text-red-500 transition-colors"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
};

export default LogEntry;