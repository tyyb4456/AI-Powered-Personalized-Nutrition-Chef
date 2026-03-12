// src/components/recipe/RecipeCard.jsx

import { Clock, ChefHat, ArrowRight } from 'lucide-react';
import { useTheme } from '../../store/ThemeContext';

const RecipeCard = ({ recipe, onClick }) => {
  const { dark } = useTheme();
  const nutrition = recipe.nutrition || recipe.nutrition_facts || {};

  return (
    <div
      onClick={onClick}
      className={`group relative p-5 rounded-2xl border cursor-pointer transition-all duration-300 hover:-translate-y-0.5 overflow-hidden ${
        dark
          ? 'bg-white/4 border-white/8 hover:border-white/15 hover:shadow-lg hover:shadow-black/40'
          : 'bg-white border-black/8 hover:border-black/15 hover:shadow-md hover:shadow-black/6'
      }`}
    >
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: 'radial-gradient(circle at 0% 0%, rgba(139,92,246,0.06) 0%, transparent 60%)' }}
      />

      <div className="relative">
        <div className="flex items-start justify-between gap-2 mb-3">
          <h3 className={`font-semibold text-sm leading-snug ${dark ? 'text-white' : 'text-gray-900'}`}>
            {recipe.dish_name}
          </h3>
          {recipe.meal_type && (
            <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${dark ? 'bg-white/8 text-gray-400' : 'bg-black/5 text-gray-500'}`}>
              {recipe.meal_type}
            </span>
          )}
        </div>

        <div className={`flex items-center gap-3 text-xs mb-4 ${dark ? 'text-gray-500' : 'text-gray-400'}`}>
          {recipe.cuisine && (
            <span className="flex items-center gap-1">
              <ChefHat size={10} />{recipe.cuisine}
            </span>
          )}
          {recipe.prep_time_minutes && (
            <span className="flex items-center gap-1">
              <Clock size={10} />{recipe.prep_time_minutes} min
            </span>
          )}
        </div>

        <div className="flex gap-2">
          <span className={`text-xs px-2.5 py-1 rounded-lg font-medium ${dark ? 'bg-amber-400/10 text-amber-400' : 'bg-amber-50 text-amber-700'}`}>
            {nutrition.calories ?? '—'} kcal
          </span>
          <span className={`text-xs px-2.5 py-1 rounded-lg font-medium ${dark ? 'bg-blue-400/10 text-blue-400' : 'bg-blue-50 text-blue-700'}`}>
            P: {nutrition.protein_g ?? '—'}g
          </span>
          <span className={`text-xs px-2.5 py-1 rounded-lg font-medium ${dark ? 'bg-orange-400/10 text-orange-400' : 'bg-orange-50 text-orange-700'}`}>
            C: {nutrition.carbs_g ?? '—'}g
          </span>
        </div>
      </div>

      <ArrowRight
        size={12}
        className={`absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-all duration-200 group-hover:translate-x-0.5 ${dark ? 'text-gray-500' : 'text-gray-400'}`}
      />
    </div>
  );
};

export default RecipeCard;