// src/components/recipe/RecipeDetail.jsx

import { useState, useEffect } from 'react';
import { Clock, ChefHat, Lightbulb, MessageSquare, CheckCircle, Loader2 } from 'lucide-react';
import MacroBadge from './MacroBadge';
import StarRating from './StarRating';
import { submitFeedback, getFeedbackForRecipe, triggerLearning } from '../../api/feedback';
import toast from 'react-hot-toast';

const RecipeDetail = ({ recipe }) => {
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [comment, setComment]           = useState('');
  const [submitting, setSubmitting]     = useState(false);
  const [rating, setRating]             = useState(0);

  // Check if feedback was already submitted for this recipe
  useEffect(() => {
    const checkExisting = async () => {
      try {
        const existing = await getFeedbackForRecipe(recipe.recipe_id);
        if (existing) setFeedbackSent(true);
      } catch {
        // No feedback yet — leave feedbackSent as false
      }
    };
    checkExisting();
  }, [recipe.recipe_id]);

  const handleFeedback = async () => {
    if (!rating) return toast.error('Please select a star rating first');
    setSubmitting(true);
    try {
      // Step 1: Save the feedback, get back feedback_id
      const fb = await submitFeedback({
        recipe_id: recipe.recipe_id,
        rating,
        comment: comment || undefined,
      });

      // Step 2: Trigger learning loop so preferences update immediately
      await triggerLearning(fb.feedback_id);

      setFeedbackSent(true);
      toast.success('Feedback submitted — AI will learn from this!');
    } catch {
      toast.error('Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  const nutrition = recipe.nutrition || recipe.nutrition_facts || recipe || {};

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">{recipe.dish_name}</h2>
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              {recipe.cuisine && (
                <span className="text-xs bg-primary-50 text-primary-700 border border-primary-200 px-2.5 py-1 rounded-full">
                  {recipe.cuisine}
                </span>
              )}
              {recipe.meal_type && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full">
                  {recipe.meal_type}
                </span>
              )}
              {recipe.prep_time_minutes && (
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <Clock size={12} />
                  {recipe.prep_time_minutes} min
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Macros */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-5">
          <MacroBadge label="Calories" value={nutrition.calories ?? '—'} unit="kcal" type="calories" />
          <MacroBadge label="Protein"  value={nutrition.protein_g ?? '—'} unit="g" type="protein" />
          <MacroBadge label="Carbs"    value={nutrition.carbs_g ?? '—'} unit="g" type="carbs" />
          <MacroBadge label="Fat"      value={nutrition.fat_g ?? '—'} unit="g" type="fat" />
          <MacroBadge label="Fiber"    value={nutrition.fiber_g ?? '—'} unit="g" type="fiber" />
        </div>
      </div>

      {/* Ingredients */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <ChefHat size={18} className="text-primary-600" />
          <h3 className="text-base font-semibold text-gray-900">Ingredients</h3>
        </div>
        <ul className="space-y-2">
          {(recipe.ingredients || []).map((ing, i) => (
            <li key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50 last:border-0">
              <span className="text-gray-800">{ing.name}</span>
              <span className="text-gray-500 font-medium">{ing.quantity}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Steps */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <CheckCircle size={18} className="text-primary-600" />
          <h3 className="text-base font-semibold text-gray-900">Instructions</h3>
        </div>
        <ol className="space-y-4">
          {(recipe.steps || []).map((step, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 font-bold text-xs flex items-center justify-center mt-0.5">
                {i + 1}
              </span>
              <p className="text-gray-700 leading-relaxed">{step}</p>
            </li>
          ))}
        </ol>
      </div>

      {/* AI Explanation */}
      {recipe.explanation && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
          <div className="flex items-center gap-2 mb-2">
            <Lightbulb size={18} className="text-amber-600" />
            <h3 className="text-base font-semibold text-amber-900">Why this recipe for you</h3>
          </div>
          <p className="text-sm text-amber-800 leading-relaxed">{recipe.explanation}</p>
        </div>
      )}

      {/* Feedback */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <MessageSquare size={18} className="text-primary-600" />
          <h3 className="text-base font-semibold text-gray-900">Rate this recipe</h3>
        </div>

        {feedbackSent ? (
          <div className="flex items-center gap-2 text-green-600 text-sm">
            <CheckCircle size={16} />
            <span>Thanks! Your feedback helps the AI improve.</span>
          </div>
        ) : (
          <div className="space-y-3">
            <StarRating onRate={setRating} disabled={submitting} />
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Optional comment — e.g. 'Too spicy, loved the protein content'"
              rows={2}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            />
            <button
              onClick={handleFeedback}
              disabled={submitting || !rating}
              className="bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting && <Loader2 size={14} className="animate-spin" />}
              Submit Feedback
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default RecipeDetail;