// src/components/recipe/RecipeCard.jsx

import { Clock, ChefHat } from 'lucide-react';

const RecipeCard = ({ recipe, onClick }) => {
  const nutrition = recipe.nutrition || recipe.nutrition_facts || {};

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl border border-gray-200 p-5 cursor-pointer hover:border-primary-400 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <h3 className="font-semibold text-gray-900 text-sm leading-snug">{recipe.dish_name}</h3>
        {recipe.meal_type && (
          <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full shrink-0">
            {recipe.meal_type}
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500 mb-3">
        {recipe.cuisine && (
          <span className="flex items-center gap-1">
            <ChefHat size={11} />
            {recipe.cuisine}
          </span>
        )}
        {recipe.prep_time_minutes && (
          <span className="flex items-center gap-1">
            <Clock size={11} />
            {recipe.prep_time_minutes} min
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <span className="text-xs bg-amber-50 text-amber-700 px-2 py-1 rounded-lg font-medium">
          {nutrition.calories ?? '—'} kcal
        </span>
        <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-lg font-medium">
          P: {nutrition.protein_g ?? '—'}g
        </span>
        <span className="text-xs bg-orange-50 text-orange-700 px-2 py-1 rounded-lg font-medium">
          C: {nutrition.carbs_g ?? '—'}g
        </span>
      </div>
    </div>
  );
};

export default RecipeCard;