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
import { useTheme } from '../../store/ThemeContext';
import toast from 'react-hot-toast';

// ── Markdown renderer ─────────────────────────────────────────────────────────
// Parses the AI explanation which comes back with **bold**, numbered lists,
// and bullet points — renders them as clean readable HTML instead of raw text.

const renderMarkdown = (text, dark) => {
  if (!text) return null;

  const textColor   = dark ? 'text-gray-300'  : 'text-gray-700';
  const boldColor   = dark ? 'text-white'      : 'text-gray-900';
  const numColor    = dark ? 'text-amber-400'  : 'text-amber-600';

  // Split into paragraphs / list items
  const lines = text.split('\n').filter(l => l.trim() !== '');

  const parseBold = (str) => {
    const parts = str.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, i) =>
      i % 2 === 1
        ? <strong key={i} className={`font-semibold ${boldColor}`}>{part}</strong>
        : <span key={i}>{part}</span>
    );
  };

  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trim();

    // Numbered list item: "1. " or "1) "
    const numMatch = line.match(/^(\d+)[.)]\s+(.*)$/);
    if (numMatch) {
      const num = numMatch[1];
      const content = numMatch[2];
      elements.push(
        <div key={i} className="flex gap-3 mt-4 first:mt-0">
          <span className={`shrink-0 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center mt-0.5 ${
            dark ? 'bg-amber-400/15 text-amber-400' : 'bg-amber-100 text-amber-700'
          }`}>
            {num}
          </span>
          <p className={`text-sm leading-relaxed ${textColor}`}>{parseBold(content)}</p>
        </div>
      );
      i++;
      continue;
    }

    // Bullet item: "* " or "- "
    const bulletMatch = line.match(/^[*\-]\s+(.*)$/);
    if (bulletMatch) {
      const content = bulletMatch[1];
      elements.push(
        <div key={i} className="flex gap-2.5 mt-2 ml-2">
          <span className={`shrink-0 w-1.5 h-1.5 rounded-full mt-2 ${dark ? 'bg-amber-400/60' : 'bg-amber-500/60'}`} />
          <p className={`text-sm leading-relaxed ${textColor}`}>{parseBold(content)}</p>
        </div>
      );
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={i} className={`text-sm leading-relaxed mt-3 first:mt-0 ${textColor}`}>
        {parseBold(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
};

// ── Chat bubble ───────────────────────────────────────────────────────────────

const ChatMessage = ({ msg, dark }) => {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
        isUser
          ? dark ? 'bg-white text-black' : 'bg-gray-900 text-white'
          : dark ? 'bg-white/10 text-gray-300' : 'bg-black/8 text-gray-600'
      }`}>
        {isUser ? <User size={11} /> : <Bot size={11} />}
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
        isUser
          ? dark
            ? 'bg-white text-black rounded-tr-sm'
            : 'bg-gray-900 text-white rounded-tr-sm'
          : dark
            ? 'bg-white/6 text-gray-200 rounded-tl-sm border border-white/8'
            : 'bg-black/5 text-gray-800 rounded-tl-sm border border-black/6'
      }`}>
        {msg.text}
      </div>
    </div>
  );
};

// ── Typing indicator ──────────────────────────────────────────────────────────

const TypingIndicator = ({ dark }) => (
  <div className="flex gap-2.5">
    <div className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${dark ? 'bg-white/10 text-gray-300' : 'bg-black/8 text-gray-600'}`}>
      <Bot size={11} />
    </div>
    <div className={`rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5 border ${
      dark ? 'bg-white/6 border-white/8' : 'bg-black/5 border-black/6'
    }`}>
      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:0ms]" />
      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:150ms]" />
      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:300ms]" />
    </div>
  </div>
);

// ── Main component ────────────────────────────────────────────────────────────

const RecipeDetail = ({ recipe: initialRecipe, onRecipeUpdate }) => {
  const { dark } = useTheme();

  const [recipe,          setRecipe]          = useState(initialRecipe);
  const [feedbackSent,    setFeedbackSent]    = useState(false);
  const [comment,         setComment]         = useState('');
  const [submitting,      setSubmitting]      = useState(false);
  const [rating,          setRating]          = useState(0);
  const [followupInput,   setFollowupInput]   = useState('');
  const [followupLoading, setFollowupLoading] = useState(false);
  const [chatHistory,     setChatHistory]     = useState([]);

  const chatEndRef = useRef(null);
  const inputRef   = useRef(null);

  useEffect(() => { setRecipe(initialRecipe); }, [initialRecipe]);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory]);
  useEffect(() => {
    const check = async () => {
      try { const e = await getFeedbackForRecipe(recipe.recipe_id); if (e) setFeedbackSent(true); } catch {}
    };
    check();
  }, [recipe.recipe_id]);

  const handleFeedback = async () => {
    if (!rating) return toast.error('Please select a star rating first');
    setSubmitting(true);
    try {
      const fb = await submitFeedback({ recipe_id: recipe.recipe_id, rating, comment: comment || undefined });
      await triggerLearning(fb.feedback_id);
      setFeedbackSent(true);
      toast.success('Feedback submitted — AI will learn from this!');
    } catch { toast.error('Failed to submit feedback'); }
    finally { setSubmitting(false); }
  };

  const handleFollowup = async () => {
    const prompt = followupInput.trim();
    if (!prompt || followupLoading) return;
    setChatHistory(p => [...p, { role: 'user', text: prompt }]);
    setFollowupInput('');
    setFollowupLoading(true);
    try {
      const result = await followupRecipe(recipe.recipe_id, prompt);
      if (result.intent === 'question') {
        setChatHistory(p => [...p, { role: 'ai', text: result.answer }]);
      } else if (result.intent === 'modify') {
        const updated = result.recipe;
        setRecipe(updated);
        onRecipeUpdate?.(updated);
        setChatHistory(p => [...p, { role: 'ai', text: `Done! Updated to "${updated.dish_name}" ✅` }]);
        toast.success('Recipe updated!');
      } else {
        setChatHistory(p => [...p, { role: 'ai', text: result.answer || 'Enjoy your meal! 🍽️' }]);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Follow-up failed. Please try again.';
      toast.error(msg);
      setChatHistory(p => [...p, { role: 'ai', text: '⚠️ Something went wrong. Please try again.' }]);
    } finally { setFollowupLoading(false); inputRef.current?.focus(); }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleFollowup(); }
  };

  const nutrition = recipe.nutrition || recipe.nutrition_facts || {};

  // Theme tokens
  const text       = dark ? 'text-white'    : 'text-gray-900';
  const muted      = dark ? 'text-gray-500' : 'text-gray-400';
  const subtext    = dark ? 'text-gray-300' : 'text-gray-700';
  const card       = dark ? 'bg-white/4 border-white/8'        : 'bg-white border-black/8';
  const divider    = dark ? 'border-white/6'                   : 'border-black/5';
  const tag        = dark ? 'bg-white/8 text-gray-300 border-white/10' : 'bg-black/5 text-gray-600 border-black/8';
  const stepNum    = dark ? 'bg-white/10 text-white'           : 'bg-black/8 text-gray-700';
  const chatHeader = dark ? 'bg-white/3 border-white/6'        : 'bg-black/2 border-black/5';
  const inputCls   = dark
    ? 'bg-white/4 border-white/8 text-white placeholder-gray-600 focus:border-white/20'
    : 'bg-black/3 border-black/10 text-gray-900 placeholder-gray-400 focus:border-black/20';
  const btnPrimary = dark
    ? 'bg-white text-black hover:bg-gray-100 disabled:opacity-30'
    : 'bg-gray-900 text-white hover:bg-black disabled:opacity-40';
  const chipCls    = dark
    ? 'text-gray-500 border-white/8 hover:border-white/20 hover:text-gray-300'
    : 'text-gray-500 border-black/10 hover:border-black/20 hover:text-gray-700';
  const sectionLabel = `text-xs font-medium tracking-widest uppercase mb-4 flex items-center gap-2 ${muted}`;

  const CHIPS = [
    { emoji: '🌱', label: 'Make it vegan' },
    { emoji: '🔥', label: 'Reduce calories by 200' },
    { emoji: '⏱️', label: 'Faster prep time' },
    { emoji: '🔄', label: 'Swap the protein' },
    { emoji: '❓', label: 'What can I substitute?' },
    { emoji: '📦', label: 'Can I meal-prep this?' },
  ];

  return (
    <div className="space-y-3">

      {/* ── Header ── */}
      <div className={`rounded-2xl border p-6 ${card}`}>
        <h2 className={`text-2xl font-bold tracking-tight mb-3 ${text}`}>{recipe.dish_name}</h2>
        <div className="flex items-center gap-2 flex-wrap">
          {recipe.cuisine && (
            <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${tag}`}>{recipe.cuisine}</span>
          )}
          {recipe.meal_type && (
            <span className={`text-xs px-2.5 py-1 rounded-full border ${tag}`}>{recipe.meal_type}</span>
          )}
          {recipe.prep_time_minutes && (
            <span className={`flex items-center gap-1 text-xs ${muted}`}>
              <Clock size={11} /> {recipe.prep_time_minutes} min
            </span>
          )}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-5">
          <MacroBadge label="Calories" value={nutrition.calories  ?? '—'} unit="kcal" type="calories" />
          <MacroBadge label="Protein"  value={nutrition.protein_g ?? '—'} unit="g"    type="protein"  />
          <MacroBadge label="Carbs"    value={nutrition.carbs_g   ?? '—'} unit="g"    type="carbs"    />
          <MacroBadge label="Fat"      value={nutrition.fat_g     ?? '—'} unit="g"    type="fat"      />
          <MacroBadge label="Fiber"    value={nutrition.fiber_g   ?? '—'} unit="g"    type="fiber"    />
        </div>
      </div>

      {/* ── Ingredients ── */}
      <div className={`rounded-2xl border p-6 ${card}`}>
        <div className={sectionLabel}><ChefHat size={13} /> Ingredients</div>
        <ul>
          {(recipe.ingredients || []).map((ing, i) => (
            <li key={i} className={`flex items-center justify-between text-sm py-2.5 border-b last:border-0 ${divider}`}>
              <span className={subtext}>{ing.name}</span>
              <span className={`font-medium tabular-nums ${muted}`}>{ing.quantity}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* ── Instructions ── */}
      {(recipe.steps || []).length > 0 && (
        <div className={`rounded-2xl border p-6 ${card}`}>
          <div className={sectionLabel}><CheckCircle size={13} /> Instructions</div>
          <ol className="space-y-4">
            {recipe.steps.map((step, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className={`shrink-0 w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center mt-0.5 ${stepNum}`}>
                  {i + 1}
                </span>
                <p className={`leading-relaxed ${subtext}`}>{step}</p>
              </li>
            ))}
          </ol>
        </div>
      )}

      {/* ── AI Explanation — rendered markdown ── */}
      {recipe.explanation && (
        <div className={`rounded-2xl border p-6 ${
          dark ? 'bg-amber-400/5 border-amber-400/12' : 'bg-amber-50/80 border-amber-200'
        }`}>
          <div className={`flex items-center gap-2 mb-4 text-xs font-semibold tracking-widest uppercase ${
            dark ? 'text-amber-400' : 'text-amber-600'
          }`}>
            <Lightbulb size={13} /> Why this recipe for you
          </div>
          {renderMarkdown(recipe.explanation, dark)}
        </div>
      )}

      {/* ── Follow-up chat ── */}
      <div className={`rounded-2xl border overflow-hidden ${card}`}>
        <div className={`flex items-center gap-2 px-5 py-3.5 border-b ${chatHeader}`}>
          <MessageSquare size={13} className={muted} />
          <span className={`text-xs font-semibold tracking-widest uppercase ${muted}`}>Ask or Modify</span>
          <span className={`text-xs ml-1 ${dark ? 'text-gray-600' : 'text-gray-400'}`}>· ask questions or request changes</span>
        </div>

        {chatHistory.length > 0 && (
          <div className="px-5 py-4 space-y-3 max-h-72 overflow-y-auto">
            {chatHistory.map((msg, i) => <ChatMessage key={i} msg={msg} dark={dark} />)}
            {followupLoading && <TypingIndicator dark={dark} />}
            <div ref={chatEndRef} />
          </div>
        )}

        <div className={`flex items-center gap-2 px-4 py-3 ${chatHistory.length > 0 ? `border-t ${divider}` : ''}`}>
          <input
            ref={inputRef}
            type="text"
            value={followupInput}
            onChange={(e) => setFollowupInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={followupLoading}
            placeholder='"Make it vegan" or "How much protein does this have?"'
            className={`flex-1 text-sm border rounded-xl px-4 py-2.5 outline-none transition-all duration-200 disabled:opacity-50 ${inputCls}`}
          />
          <button
            onClick={handleFollowup}
            disabled={!followupInput.trim() || followupLoading}
            className={`shrink-0 p-2.5 rounded-xl transition-all duration-200 ${btnPrimary}`}
          >
            {followupLoading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          </button>
        </div>

        {chatHistory.length === 0 && (
          <div className="px-4 pb-4 flex flex-wrap gap-2">
            {CHIPS.map(({ emoji, label }) => (
              <button
                key={label}
                type="button"
                onClick={() => { setFollowupInput(label); inputRef.current?.focus(); }}
                className={`text-xs border px-3 py-1.5 rounded-full transition-all duration-200 ${chipCls}`}
              >
                {emoji} {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Rate this recipe ── */}
      <div className={`rounded-2xl border p-6 ${card}`}>
        <div className={sectionLabel}><MessageSquare size={13} /> Rate this recipe</div>
        {feedbackSent ? (
          <div className={`flex items-center gap-2 text-sm ${dark ? 'text-green-400' : 'text-green-600'}`}>
            <CheckCircle size={15} />
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
              className={`w-full px-4 py-3 border rounded-xl text-sm outline-none resize-none transition-all duration-200 ${inputCls}`}
            />
            <button
              onClick={handleFeedback}
              disabled={submitting || !rating}
              className={`px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition-all duration-200 ${btnPrimary}`}
            >
              {submitting && <Loader2 size={13} className="animate-spin" />}
              Submit Feedback
            </button>
          </div>
        )}
      </div>

    </div>
  );
};

export default RecipeDetail;