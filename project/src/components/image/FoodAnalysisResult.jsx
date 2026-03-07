// src/components/image/FoodAnalysisResult.jsx

import { CheckCircle, AlertCircle, ChefHat } from 'lucide-react';
import MacroBadge from '../recipe/MacroBadge';

const CONFIDENCE_STYLES = {
  high:   'bg-green-50  text-green-700  border-green-200',
  medium: 'bg-amber-50  text-amber-700  border-amber-200',
  low:    'bg-red-50    text-red-700    border-red-200',
};

const CONFIDENCE_ICONS = {
  high:   <CheckCircle size={13} />,
  medium: <AlertCircle size={13} />,
  low:    <AlertCircle size={13} />,
};

const FoodAnalysisResult = ({ result, onLogThis }) => {
  const nutrition = result.estimated_nutrition || {};

  return (
    <div className="space-y-5">

      {/* Identified items */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <ChefHat size={17} className="text-primary-600" />
            <h3 className="text-sm font-semibold text-gray-900">Identified Food</h3>
          </div>
          {result.confidence_overall && (
            <span className={`flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full border ${CONFIDENCE_STYLES[result.confidence_overall] || CONFIDENCE_STYLES.medium}`}>
              {CONFIDENCE_ICONS[result.confidence_overall]}
              {result.confidence_overall} confidence
            </span>
          )}
        </div>

        {/* Dish summary */}
        {result.dish_summary && (
          <p className="text-base font-semibold text-gray-800 mb-3">{result.dish_summary}</p>
        )}

        {/* Individual items */}
        <ul className="space-y-2">
          {(result.identified_items || []).map((item, i) => (
            <li key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50 last:border-0">
              <div className="flex items-center gap-2">
                <span className="text-gray-800 font-medium">{item.name}</span>
                <span className="text-gray-400 text-xs">{item.estimated_amount}</span>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full border ${CONFIDENCE_STYLES[item.confidence] || CONFIDENCE_STYLES.medium}`}>
                {item.confidence}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* Nutrition estimate */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Estimated Nutrition</h3>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <MacroBadge label="Calories" value={nutrition.calories  ?? '—'} unit="kcal" type="calories" />
          <MacroBadge label="Protein"  value={nutrition.protein_g ?? '—'} unit="g"    type="protein"  />
          <MacroBadge label="Carbs"    value={nutrition.carbs_g   ?? '—'} unit="g"    type="carbs"    />
          <MacroBadge label="Fat"      value={nutrition.fat_g     ?? '—'} unit="g"    type="fat"      />
          <MacroBadge label="Fiber"    value={nutrition.fiber_g   ?? '—'} unit="g"    type="fiber"    />
        </div>
      </div>

      {/* Analysis notes */}
      {result.analysis_notes && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          <p className="text-xs text-amber-700">
            <span className="font-semibold">⚠️ Note: </span>
            {result.analysis_notes}
          </p>
        </div>
      )}

      {/* Log this meal CTA */}
      {onLogThis && (
        <button
          onClick={onLogThis}
          className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
        >
          ✅ Log This Meal
        </button>
      )}
    </div>
  );
};

export default FoodAnalysisResult;