// src/components/mealplan/DayColumn.jsx

import MealSlotCard from './MealSlotCard';

const SLOTS = ['breakfast', 'lunch', 'dinner', 'snack'];

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const DayColumn = ({ dayNumber, meals }) => {
  // meals is an object keyed by slot: { breakfast: {...}, lunch: {...} }
  const label = DAYS[(dayNumber - 1) % 7] || `Day ${dayNumber}`;

  // Calculate total calories for the day
  const totalCals = SLOTS.reduce((sum, slot) => {
    const nutrition = meals?.[slot]?.nutrition || meals?.[slot]?.nutrition_facts || {};
    return sum + (nutrition.calories || 0);
  }, 0);

  return (
    <div className="flex flex-col min-w-40">
      {/* Day header */}
      <div className="bg-white border border-gray-200 rounded-t-xl px-3 py-2 text-center sticky top-0 z-10">
        <p className="text-sm font-bold text-gray-900">{label}</p>
        {totalCals > 0 && (
          <p className="text-xs text-gray-400">{totalCals} kcal</p>
        )}
      </div>

      {/* Meal slots */}
      <div className="flex flex-col gap-2 bg-gray-50 border border-t-0 border-gray-200 rounded-b-xl p-2">
        {SLOTS.map((slot) => (
          <MealSlotCard
            key={slot}
            slot={slot}
            meal={meals?.[slot] || null}
          />
        ))}
      </div>
    </div>
  );
};

export default DayColumn;