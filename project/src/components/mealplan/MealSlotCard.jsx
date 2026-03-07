// src/components/mealplan/MealSlotCard.jsx

const SLOT_COLORS = {
  breakfast: 'border-l-amber-400  bg-amber-50',
  lunch:     'border-l-green-400  bg-green-50',
  dinner:    'border-l-blue-400   bg-blue-50',
  snack:     'border-l-purple-400 bg-purple-50',
};

const SLOT_LABEL_COLORS = {
  breakfast: 'text-amber-600',
  lunch:     'text-green-600',
  dinner:    'text-blue-600',
  snack:     'text-purple-600',
};

const SLOT_ICONS = {
  breakfast: '🌅',
  lunch:     '☀️',
  dinner:    '🌙',
  snack:     '🍎',
};

const MealSlotCard = ({ slot, meal }) => {
  if (!meal) {
    return (
      <div className={`border-l-4 border-l-gray-200 bg-gray-50 rounded-lg p-3`}>
        <p className={`text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1`}>
          {SLOT_ICONS[slot]} {slot}
        </p>
        <p className="text-xs text-gray-300 italic">No meal planned</p>
      </div>
    );
  }

  const nutrition = meal.nutrition || meal.nutrition_facts || {};

  return (
    <div className={`border-l-4 ${SLOT_COLORS[slot] || 'border-l-gray-300 bg-gray-50'} rounded-lg p-3`}>
      <p className={`text-xs font-semibold uppercase tracking-wide mb-1 ${SLOT_LABEL_COLORS[slot] || 'text-gray-500'}`}>
        {SLOT_ICONS[slot]} {slot}
      </p>
      <p className="text-sm font-medium text-gray-800 leading-snug">{meal.dish_name}</p>
      {nutrition.calories && (
        <p className="text-xs text-gray-500 mt-1">{nutrition.calories} kcal</p>
      )}
    </div>
  );
};

export default MealSlotCard;