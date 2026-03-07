// src/pages/MealPlanPage.jsx

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarDays, Loader2, RefreshCw, ShoppingCart, CalendarClock, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { getActivePlan, generateMealPlan } from '../api/mealPlans';
import DayColumn from '../components/mealplan/DayColumn';
import GroceryList from '../components/mealplan/GroceryList';
import PrepSchedule from '../components/mealplan/PrepSchedule';

const TABS = [
  { id: 'plan',    label: 'Weekly Plan',     icon: CalendarDays },
  { id: 'grocery', label: 'Grocery List',    icon: ShoppingCart },
  { id: 'prep',    label: 'Prep Schedule',   icon: CalendarClock },
];

// Normalize the days structure from the backend response
const normalizeDays = (plan) => {
  if (!plan) return {};

  // Format: { days: [ { day_number, meals: { breakfast, lunch, dinner, snack } } ] }
  if (Array.isArray(plan.days)) {
    return plan.days.reduce((acc, day) => {
      acc[day.day_number] = day.meals || day;
      return acc;
    }, {});
  }

  // Format: { day_1: {...}, day_2: {...} }
  if (plan.day_1 || plan.day_2) {
    return Object.fromEntries(
      Object.entries(plan)
        .filter(([k]) => k.startsWith('day_'))
        .map(([k, v]) => [k.replace('day_', ''), v])
    );
  }

  return {};
};

const MealPlanPage = () => {
  const [activeTab, setActiveTab] = useState('plan');
  const [generating, setGenerating] = useState(false);
  const queryClient = useQueryClient();

  const { data: plan, isLoading, isError } = useQuery({
    queryKey: ['activePlan'],
    queryFn: getActivePlan,
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: generateMealPlan,
    onMutate: () => setGenerating(true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activePlan'] });
      toast.success('7-day meal plan generated!');
      setGenerating(false);
      setActiveTab('plan');
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Generation failed. Make sure your profile is complete.';
      toast.error(msg);
      setGenerating(false);
    },
  });

  const days = normalizeDays(plan);
  const hasPlan = Object.keys(days).length > 0;
  const planId = plan?.plan_id;

  return (
    <div className="p-6 max-w-7xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-50 rounded-lg">
            <CalendarDays className="text-primary-600" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Meal Plan</h1>
            <p className="text-sm text-gray-500">Your personalized 7-day nutrition plan</p>
          </div>
        </div>

        <button
          onClick={() => mutation.mutate()}
          disabled={generating}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {generating ? (
            <><Loader2 size={15} className="animate-spin" /> Generating...</>
          ) : (
            <><RefreshCw size={15} /> {hasPlan ? 'Regenerate Plan' : 'Generate Plan'}</>
          )}
        </button>
      </div>

      {/* Long generation warning */}
      {generating && (
        <div className="flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <AlertTriangle size={18} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-amber-800">Generating your 7-day plan</p>
            <p className="text-xs text-amber-700 mt-0.5">
              This takes 90–180 seconds — the AI is crafting 28 personalized meals, a grocery list, and a prep schedule. Please wait.
            </p>
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center h-60">
          <Loader2 className="animate-spin text-primary-600" size={28} />
        </div>
      )}

      {/* No plan yet */}
      {!isLoading && !generating && (isError || !hasPlan) && (
        <div className="text-center py-20">
          <CalendarDays size={48} className="mx-auto text-gray-200 mb-4" />
          <p className="text-gray-500 font-medium text-lg">No meal plan yet</p>
          <p className="text-sm text-gray-400 mt-1 mb-6">
            Generate a 7-day plan tailored to your health profile
          </p>
          <button
            onClick={() => mutation.mutate()}
            disabled={generating}
            className="bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold px-6 py-3 rounded-xl transition-colors disabled:opacity-60"
          >
            Generate My Plan
          </button>
        </div>
      )}

      {/* Plan exists — show tabs */}
      {!isLoading && hasPlan && !generating && (
        <>
          {/* Tabs */}
          <div className="flex gap-1 bg-gray-100 p-1 rounded-xl mb-6 w-fit">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                  activeTab === id
                    ? 'bg-white text-primary-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </div>

          {/* Weekly grid */}
          {activeTab === 'plan' && (
            <div className="overflow-x-auto pb-4">
              <div className="flex gap-3" style={{ minWidth: 'max-content' }}>
                {[1, 2, 3, 4, 5, 6, 7].map((dayNum) => (
                  <DayColumn
                    key={dayNum}
                    dayNumber={dayNum}
                    meals={days[dayNum] || days[String(dayNum)] || {}}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Grocery List */}
          {activeTab === 'grocery' && planId && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-2xl">
              <GroceryList planId={planId} />
            </div>
          )}

          {/* Prep Schedule */}
          {activeTab === 'prep' && planId && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-2xl">
              <PrepSchedule planId={planId} />
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default MealPlanPage;