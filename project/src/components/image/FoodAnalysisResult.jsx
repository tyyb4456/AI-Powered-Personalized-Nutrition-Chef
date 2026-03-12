// src/components/image/FoodAnalysisResult.jsx

import { CheckCircle, AlertCircle, ChefHat } from 'lucide-react';
import MacroBadge from '../recipe/MacroBadge';
import { useTheme } from '../../store/ThemeContext';

const CONF_DARK = {
  high:   'bg-green-400/10 text-green-400 border-green-400/20',
  medium: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
  low:    'bg-red-400/10   text-red-400   border-red-400/20',
};
const CONF_LIGHT = {
  high:   'bg-green-50  text-green-700  border-green-200',
  medium: 'bg-amber-50  text-amber-700  border-amber-200',
  low:    'bg-red-50    text-red-700    border-red-200',
};

const FoodAnalysisResult = ({ result, onLogThis }) => {
  const { dark } = useTheme();
  const nutrition = result.estimated_nutrition || {};
  const CONF = dark ? CONF_DARK : CONF_LIGHT;

  const divider = dark ? 'border-white/6' : 'border-black/6';
  const text    = dark ? 'text-white' : 'text-gray-900';
  const muted   = dark ? 'text-gray-500' : 'text-gray-400';
  const section = dark ? 'bg-white/3 border-white/6' : 'bg-black/2 border-black/6';

  return (
    <div className="space-y-5">

      {/* Identified items */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ChefHat size={14} className={muted} />
            <span className={`text-xs font-medium tracking-wide uppercase ${muted}`}>Identified Food</span>
          </div>
          {result.confidence_overall && (
            <span className={`flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full border ${CONF[result.confidence_overall] || CONF.medium}`}>
              {result.confidence_overall === 'high' ? <CheckCircle size={11} /> : <AlertCircle size={11} />}
              {result.confidence_overall} confidence
            </span>
          )}
        </div>

        {result.dish_summary && (
          <p className={`text-base font-semibold mb-4 ${text}`}>{result.dish_summary}</p>
        )}

        <ul className="space-y-1">
          {(result.identified_items || []).map((item, i) => (
            <li key={i} className={`flex items-center justify-between text-sm py-2 border-b last:border-0 ${divider}`}>
              <div className="flex items-center gap-2">
                <span className={`font-medium ${text}`}>{item.name}</span>
                <span className={`text-xs ${muted}`}>{item.estimated_amount}</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${CONF[item.confidence] || CONF.medium}`}>
                {item.confidence}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Nutrition */}
      <div className={`rounded-xl border p-4 ${section}`}>
        <span className={`text-xs font-medium tracking-wide uppercase block mb-4 ${muted}`}>Estimated Nutrition</span>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <MacroBadge label="Calories" value={nutrition.calories  ?? '—'} unit="kcal" type="calories" />
          <MacroBadge label="Protein"  value={nutrition.protein_g ?? '—'} unit="g"    type="protein"  />
          <MacroBadge label="Carbs"    value={nutrition.carbs_g   ?? '—'} unit="g"    type="carbs"    />
          <MacroBadge label="Fat"      value={nutrition.fat_g     ?? '—'} unit="g"    type="fat"      />
          <MacroBadge label="Fiber"    value={nutrition.fiber_g   ?? '—'} unit="g"    type="fiber"    />
        </div>
      </div>

      {result.analysis_notes && (
        <div className={`rounded-xl border px-4 py-3 ${dark ? 'bg-amber-400/8 border-amber-400/15' : 'bg-amber-50 border-amber-200'}`}>
          <p className={`text-xs ${dark ? 'text-amber-400' : 'text-amber-700'}`}>
            <span className="font-semibold">Note: </span>{result.analysis_notes}
          </p>
        </div>
      )}

      {onLogThis && (
        <button
          onClick={onLogThis}
          className={`w-full py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-200 ${
            dark ? 'bg-white text-black hover:bg-gray-100' : 'bg-gray-900 text-white hover:bg-black'
          }`}
        >
          Log This Meal
        </button>
      )}
    </div>
  );
};

export default FoodAnalysisResult;