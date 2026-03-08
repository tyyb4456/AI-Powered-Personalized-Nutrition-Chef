// src/pages/DashboardPage.jsx

import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, CalendarDays, ClipboardList, Camera, Leaf, Loader2, TrendingUp } from 'lucide-react';
import { useAuth } from '../store/AuthContext';
import { getMealLogs, getDailyAdherence } from '../api/mealLogs';
import { listRecipes } from '../api/recipes';

const toISODate = (d) => d.toISOString().split('T')[0];

const QuickAction = ({ icon: Icon, label, desc, color, onClick }) => (
  <button
    onClick={onClick}
    className="bg-white rounded-xl border border-gray-200 p-5 text-left hover:border-primary-300 hover:shadow-sm transition-all group"
  >
    <div className={`inline-flex p-2.5 rounded-lg mb-3 ${color}`}>
      <Icon size={20} className="text-white" />
    </div>
    <p className="text-sm font-semibold text-gray-900 group-hover:text-primary-700 transition-colors">
      {label}
    </p>
    <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
  </button>
);

const StatCard = ({ label, value, unit, color, loading }) => (
  <div className="bg-white rounded-xl border border-gray-200 p-5">
    {loading ? (
      <div className="flex items-center justify-center h-12">
        <Loader2 className="animate-spin text-gray-300" size={18} />
      </div>
    ) : (
      <>
        <p className={`text-2xl font-bold ${color}`}>
          {value ?? '—'}
          {unit && <span className="text-xs font-normal text-gray-400 ml-0.5">{unit}</span>}
        </p>
        <p className="text-xs text-gray-500 mt-1">{label}</p>
      </>
    )}
  </div>
);

const DashboardPage = () => {
  const { user } = useAuth();
  const navigate  = useNavigate();
  const today     = toISODate(new Date());

  const { data: adherence, isLoading: adherenceLoading } = useQuery({
    queryKey: ['adherence', today],
    queryFn:  () => getDailyAdherence(today),
    retry:    false,
  });

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['mealLogs', today],
    queryFn:  () => getMealLogs({ dateFrom: today, dateTo: today }),
    retry:    false,
  });

  const { data: recipesData, isLoading: recipesLoading } = useQuery({
    queryKey: ['recipes', 1],
    queryFn:  () => listRecipes({ page: 1, limit: 1 }),
    retry:    false,
  });

  const pct          = Math.min(adherence?.adherence_pct || 0, 100);
  const actualCals   = adherence?.actual_calories  || 0;
  const plannedCals  = adherence?.planned_calories || 0;
  const mealsLogged  = logsData?.logs?.length      || 0;
  const totalRecipes = recipesData?.total          || 0;

  const barColor =
    pct >= 90 ? 'bg-green-500' :
    pct >= 60 ? 'bg-amber-400' :
                'bg-red-400';

  return (
    <div className="p-6 max-w-5xl mx-auto">

      {/* Welcome */}
      <div className="flex items-center gap-3 mb-8">
        <div className="p-2.5 bg-primary-50 rounded-xl">
          <Leaf className="text-primary-600" size={26} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'},{' '}
            {user?.name} 👋
          </h1>
          <p className="text-sm text-gray-500">
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
          </p>
        </div>
      </div>

      {/* Today's calorie progress */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <TrendingUp size={16} className="text-primary-600" />
            <h2 className="text-sm font-semibold text-gray-900">Today's Calorie Progress</h2>
          </div>
          <button
            onClick={() => navigate('/meal-log')}
            className="text-xs text-primary-600 hover:underline font-medium"
          >
            Log a meal →
          </button>
        </div>

        {adherenceLoading ? (
          <div className="flex items-center justify-center h-12">
            <Loader2 className="animate-spin text-gray-300" size={18} />
          </div>
        ) : (
          <>
            <div className="flex items-end justify-between mb-2">
              <span className="text-3xl font-bold text-gray-900">{actualCals}</span>
              <span className="text-sm text-gray-400">/ {plannedCals} kcal</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-3 mb-2">
              <div
                className={`h-3 rounded-full transition-all duration-700 ${barColor}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-xs text-gray-400">{pct.toFixed(0)}% of daily target</p>
          </>
        )}
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Meals Today"
          value={mealsLogged}
          color="text-primary-600"
          loading={logsLoading}
        />
        <StatCard
          label="Calories Today"
          value={actualCals}
          unit="kcal"
          color="text-amber-600"
          loading={adherenceLoading}
        />
        <StatCard
          label="Adherence"
          value={`${pct.toFixed(0)}%`}
          color={pct >= 90 ? 'text-green-600' : pct >= 60 ? 'text-amber-600' : 'text-red-500'}
          loading={adherenceLoading}
        />
        <StatCard
          label="Total Recipes"
          value={totalRecipes}
          color="text-blue-600"
          loading={recipesLoading}
        />
      </div>

      {/* Quick actions */}
      <h2 className="text-sm font-semibold text-gray-700 mb-3">Quick Actions</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <QuickAction
          icon={Sparkles}
          label="Generate Recipe"
          desc="AI-crafted meal for you"
          color="bg-primary-600"
          onClick={() => navigate('/recipes/generate')}
        />
        <QuickAction
          icon={ClipboardList}
          label="Log a Meal"
          desc="Track what you ate"
          color="bg-amber-500"
          onClick={() => navigate('/meal-log')}
        />
        <QuickAction
          icon={Camera}
          label="Food Camera"
          desc="Snap & identify food"
          color="bg-purple-500"
          onClick={() => navigate('/food-camera')}
        />
        <QuickAction
          icon={CalendarDays}
          label="Meal Plan"
          desc="View your 7-day plan"
          color="bg-blue-500"
          onClick={() => navigate('/meal-plan')}
        />
      </div>
    </div>
  );
};

export default DashboardPage;