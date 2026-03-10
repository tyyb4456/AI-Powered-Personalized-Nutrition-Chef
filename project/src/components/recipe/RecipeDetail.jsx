// src/components/recipe/RecipeDetail.jsx

import { useState, useRef, useEffect } from 'react';
import {
  Clock, ChefHat, Lightbulb, MessageSquare,
  CheckCircle, Loader2, Send, Bot, User,
} from 'lucide-react';
import MacroBadge from './MacroBadge';
import StarRating from './StarRating';
import { submitFeedback, getFeedbackForRecipe, triggerLearning } from '../../api/feedback';
import { followupRecipe } from '../../api/recipes';
import toast from 'react-hot-toast';

// ── Chat bubble ───────────────────────────────────────────────────────────────

const ChatMessage = ({ msg }) => {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-white ${
        isUser ? 'bg-primary-600' : 'bg-gray-700'
      }`}>
        {isUser ? <User size={13} /> : <Bot size={13} />}
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
        isUser
          ? 'bg-primary-600 text-white rounded-tr-sm'
          : 'bg-gray-100 text-gray-800 rounded-tl-sm'
      }`}>
        {msg.text}
      </div>
    </div>
  );
};

// ── Main component ────────────────────────────────────────────────────────────

/**
 * RecipeDetail
 *
 * Props:
 *   recipe          – the recipe object to display (required)
 *   onRecipeUpdate  – optional callback(newRecipe) called when the AI regenerates
 *                     the recipe via a "modify" follow-up. Used by GenerateRecipePage
 *                     to swap out the displayed recipe. When not provided (e.g. on
 *                     RecipesPage), a regenerated recipe is shown inline only.
 */
const RecipeDetail = ({ recipe: initialRecipe, onRecipeUpdate }) => {
  // ── Local recipe state — supports in-place swapping on modify ──────────────
  const [recipe, setRecipe] = useState(initialRecipe);

  // Keep in sync if parent passes a new recipe (e.g. after generate)
  useEffect(() => { setRecipe(initialRecipe); }, [initialRecipe]);

  // ── Feedback state ────────────────────────────────────────────────────────
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [comment,      setComment]      = useState('');
  const [submitting,   setSubmitting]   = useState(false);
  const [rating,       setRating]       = useState(0);

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

  // ── Follow-up state ───────────────────────────────────────────────────────
  const [followupInput,   setFollowupInput]   = useState('');
  const [followupLoading, setFollowupLoading] = useState(false);
  const [chatHistory,     setChatHistory]     = useState([]);

  const chatEndRef = useRef(null);
  const inputRef   = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // ── Feedback handler ──────────────────────────────────────────────────────
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

  // ── Follow-up handler ─────────────────────────────────────────────────────
  const handleFollowup = async () => {
    const prompt = followupInput.trim();
    if (!prompt || followupLoading) return;

    setChatHistory((prev) => [...prev, { role: 'user', text: prompt }]);
    setFollowupInput('');
    setFollowupLoading(true);

    try {
      const result = await followupRecipe(recipe.recipe_id, prompt);

      if (result.intent === 'question') {
        setChatHistory((prev) => [...prev, { role: 'ai', text: result.answer }]);

      } else if (result.intent === 'modify') {
        const updated = result.recipe;
        // Update locally so the detail view reflects the new recipe immediately
        setRecipe(updated);
        // Notify parent (GenerateRecipePage) if it cares
        onRecipeUpdate?.(updated);
        setChatHistory((prev) => [
          ...prev,
          { role: 'ai', text: `Done! I've updated this to "${updated.dish_name}". ✅` },
        ]);
        toast.success('Recipe updated!');

      } else {
        setChatHistory((prev) => [
          ...prev,
          { role: 'ai', text: result.answer || 'Enjoy your meal! 🍽️' },
        ]);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Follow-up failed. Please try again.';
      toast.error(msg);
      setChatHistory((prev) => [
        ...prev,
        { role: 'ai', text: '⚠️ Something went wrong. Please try again.' },
      ]);
    } finally {
      setFollowupLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleFollowup();
    }
  };

  const nutrition = recipe.nutrition || recipe.nutrition_facts || {};

  // ── Render ────────────────────────────────────────────────────────────────
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
          <MacroBadge label="Calories" value={nutrition.calories   ?? '—'} unit="kcal" type="calories" />
          <MacroBadge label="Protein"  value={nutrition.protein_g  ?? '—'} unit="g"    type="protein"  />
          <MacroBadge label="Carbs"    value={nutrition.carbs_g    ?? '—'} unit="g"    type="carbs"    />
          <MacroBadge label="Fat"      value={nutrition.fat_g      ?? '—'} unit="g"    type="fat"      />
          <MacroBadge label="Fiber"    value={nutrition.fiber_g    ?? '—'} unit="g"    type="fiber"    />
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
      {(recipe.steps || []).length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle size={18} className="text-primary-600" />
            <h3 className="text-base font-semibold text-gray-900">Instructions</h3>
          </div>
          <ol className="space-y-4">
            {recipe.steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="shrink-0 w-6 h-6 rounded-full bg-primary-100 text-primary-700 font-bold text-xs flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <p className="text-gray-700 leading-relaxed">{step}</p>
              </li>
            ))}
          </ol>
        </div>
      )}

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

      {/* ── Follow-up chat ──────────────────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">

        {/* Header */}
        <div className="flex items-center gap-2 px-5 py-3.5 bg-gray-50 border-b border-gray-100">
          <MessageSquare size={15} className="text-primary-600" />
          <span className="text-sm font-semibold text-gray-700">Ask or modify</span>
          <span className="text-xs text-gray-400 ml-1">Ask questions or request changes</span>
        </div>

        {/* Chat history */}
        {chatHistory.length > 0 && (
          <div className="px-5 py-4 space-y-3 max-h-72 overflow-y-auto">
            {chatHistory.map((msg, i) => (
              <ChatMessage key={i} msg={msg} />
            ))}

            {/* Typing indicator */}
            {followupLoading && (
              <div className="flex gap-3">
                <div className="shrink-0 w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center">
                  <Bot size={13} className="text-white" />
                </div>
                <div className="bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-2.5 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        )}

        {/* Input bar */}
        <div className={`flex items-center gap-2 px-4 py-3 ${chatHistory.length > 0 ? 'border-t border-gray-100' : ''}`}>
          <input
            ref={inputRef}
            type="text"
            value={followupInput}
            onChange={(e) => setFollowupInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={followupLoading}
            placeholder='e.g. "Make it vegan" or "How much protein does this have?"'
            className="flex-1 text-sm bg-gray-50 border border-gray-200 rounded-lg px-4 py-2.5 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-300 focus:border-primary-400 disabled:opacity-50 transition-all"
          />
          <button
            onClick={handleFollowup}
            disabled={!followupInput.trim() || followupLoading}
            className="shrink-0 bg-primary-600 hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed text-white p-2.5 rounded-lg transition-colors"
          >
            {followupLoading
              ? <Loader2 size={16} className="animate-spin" />
              : <Send size={16} />
            }
          </button>
        </div>

        {/* Prompt suggestion chips — only before first message */}
        {chatHistory.length === 0 && (
          <div className="px-4 pb-3 flex flex-wrap gap-2">
            {[
              { emoji: '🌱', label: 'Make it vegan' },
              { emoji: '🔥', label: 'Reduce calories by 200' },
              { emoji: '⏱️', label: 'Faster prep time' },
              { emoji: '🔄', label: 'Swap the protein' },
              { emoji: '❓', label: 'What can I substitute?' },
              { emoji: '📦', label: 'Can I meal-prep this?' },
            ].map(({ emoji, label }) => (
              <button
                key={label}
                onClick={() => {
                  setFollowupInput(label);
                  inputRef.current?.focus();
                }}
                className="text-xs text-gray-500 border border-gray-200 hover:border-primary-300 hover:text-primary-600 px-3 py-1.5 rounded-full transition-colors"
              >
                {emoji} {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Rate this recipe ────────────────────────────────────────────────── */}
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