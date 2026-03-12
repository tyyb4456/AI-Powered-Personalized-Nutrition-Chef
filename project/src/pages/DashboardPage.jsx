// src/pages/DashboardPage.jsx

import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Sparkles, CalendarDays, ClipboardList, Camera, Leaf, Loader2, TrendingUp, ArrowRight } from 'lucide-react';
import { useAuth } from '../store/AuthContext';
import { useTheme } from '../store/ThemeContext';
import { getMealLogs, getDailyAdherence } from '../api/mealLogs';
import { listRecipes } from '../api/recipes';

const toISODate = (d) => d.toISOString().split('T')[0];

const QuickAction = ({ icon: Icon, label, desc, accent, onClick, dark }) => (
  <button
    onClick={onClick}
    className={`group relative text-left p-5 rounded-2xl border transition-all duration-300 overflow-hidden hover:-translate-y-0.5 hover:shadow-lg ${
      dark
        ? 'bg-white/4 border-white/8 hover:border-white/15 hover:shadow-black/40'
        : 'bg-white border-black/8 hover:border-black/15 hover:shadow-black/8'
    }`}
  >
    <div
      className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
      style={{ background: `radial-gradient(circle at 0% 0%, ${accent}18 0%, transparent 60%)` }}
    />
    <div className="relative">
      <div className="mb-4 inline-flex p-2.5 rounded-xl" style={{ background: `${accent}18` }}>
        <Icon size={16} style={{ color: accent }} />
      </div>
      <p className={`text-sm font-semibold mb-1 ${dark ? 'text-white' : 'text-gray-900'}`}>{label}</p>
      <p className={`text-xs ${dark ? 'text-gray-500' : 'text-gray-400'}`}>{desc}</p>
    </div>
    <ArrowRight
      size={12}
      className={`absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-all duration-200 group-hover:translate-x-0.5 ${dark ? 'text-gray-400' : 'text-gray-400'}`}
    />
  </button>
);

const StatCard = ({ label, value, unit, accent, loading, dark }) => (
  <div className={`p-5 rounded-2xl border transition-colors duration-300 ${
    dark ? 'bg-white/4 border-white/8' : 'bg-white border-black/8'
  }`}>
    {loading ? (
      <div className="flex items-center justify-center h-12">
        <Loader2 className={`animate-spin ${dark ? 'text-white/20' : 'text-gray-200'}`} size={16} />
      </div>
    ) : (
      <>
        <p className="text-2xl font-bold tracking-tight" style={{ color: accent }}>
          {value ?? '—'}
          {unit && <span className={`text-xs font-normal ml-1 ${dark ? 'text-gray-500' : 'text-gray-400'}`}>{unit}</span>}
        </p>
        <p className={`text-xs mt-1 ${dark ? 'text-gray-500' : 'text-gray-400'}`}>{label}</p>
      </>
    )}
  </div>
);

const DashboardPage = () => {
  const { user } = useAuth();
  const { dark } = useTheme();
  const navigate = useNavigate();
  const today = toISODate(new Date());

  const { data: adherence, isLoading: adherenceLoading } = useQuery({
    queryKey: ['adherence', today],
    queryFn: () => getDailyAdherence(today),
    retry: false,
  });

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['mealLogs', today],
    queryFn: () => getMealLogs({ dateFrom: today, dateTo: today }),
    retry: false,
  });

  const { data: recipesData, isLoading: recipesLoading } = useQuery({
    queryKey: ['recipes', 1],
    queryFn: () => listRecipes({ page: 1, limit: 1 }),
    retry: false,
  });

  const pct         = Math.min(adherence?.adherence_pct || 0, 100);
  const actualCals  = adherence?.actual_calories || 0;
  const plannedCals = adherence?.planned_calories || 0;
  const mealsLogged = logsData?.logs?.length || 0;
  const totalRecipes = recipesData?.total || 0;

  const barColor = pct >= 90 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444';

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  const text = dark ? 'text-white' : 'text-gray-900';
  const muted = dark ? 'text-gray-500' : 'text-gray-400';
  const card = dark ? 'bg-white/4 border-white/8' : 'bg-white border-black/8';

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-3">
          <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
            <Leaf size={15} className={text} />
          </div>
          <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>Dashboard</span>
        </div>
        <h1 className={`text-3xl font-bold tracking-tight ${text}`}>
          {greeting}, <span className={dark ? 'text-gray-300' : 'text-gray-600'}>{user?.name}</span>
        </h1>
        <p className={`text-sm mt-1 ${muted}`}>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
        </p>
      </div>

      {/* Calorie Progress */}
      <div className={`rounded-2xl border p-6 mb-6 transition-colors duration-300 ${card}`}>
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <TrendingUp size={14} className={muted} />
            <span className={`text-xs font-medium tracking-wide uppercase ${muted}`}>Today's Progress</span>
          </div>
          <button
            onClick={() => navigate('/meal-log')}
            className={`text-xs font-medium flex items-center gap-1 transition-colors ${
              dark ? 'text-gray-500 hover:text-white' : 'text-gray-400 hover:text-gray-900'
            }`}
          >
            Log meal <ArrowRight size={11} />
          </button>
        </div>

        {adherenceLoading ? (
          <div className="flex items-center justify-center h-16">
            <Loader2 className={`animate-spin ${dark ? 'text-white/20' : 'text-gray-200'}`} size={18} />
          </div>
        ) : (
          <>
            <div className="flex items-baseline justify-between mb-3">
              <span className={`text-4xl font-bold tracking-tight ${text}`}>{actualCals}</span>
              <span className={`text-sm ${muted}`}>/ {plannedCals} kcal</span>
            </div>
            <div className={`w-full h-1.5 rounded-full mb-2 ${dark ? 'bg-white/8' : 'bg-black/8'}`}>
              <div
                className="h-1.5 rounded-full transition-all duration-700"
                style={{ width: `${pct}%`, backgroundColor: barColor }}
              />
            </div>
            <p className={`text-xs ${muted}`}>{pct.toFixed(0)}% of daily target</p>
          </>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <StatCard label="Meals Today"    value={mealsLogged}           accent={dark ? '#a3a3a3' : '#6b7280'} loading={logsLoading}      dark={dark} />
        <StatCard label="Calories"       value={actualCals} unit="kcal" accent="#f59e0b"                     loading={adherenceLoading}  dark={dark} />
        <StatCard label="Adherence"      value={`${pct.toFixed(0)}%`}  accent={barColor}                    loading={adherenceLoading}  dark={dark} />
        <StatCard label="Saved Recipes"  value={totalRecipes}          accent="#3b82f6"                      loading={recipesLoading}    dark={dark} />
      </div>

      {/* Quick Actions */}
      <div className="mb-4">
        <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>Quick Actions</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <QuickAction icon={Sparkles}      label="Generate Recipe" desc="AI-crafted meal"       accent="#8b5cf6" onClick={() => navigate('/recipes/generate')} dark={dark} />
        <QuickAction icon={ClipboardList} label="Log a Meal"      desc="Track what you ate"   accent="#f59e0b" onClick={() => navigate('/meal-log')}         dark={dark} />
        <QuickAction icon={Camera}        label="Food Camera"     desc="Snap & identify food"  accent="#ec4899" onClick={() => navigate('/food-camera')}      dark={dark} />
        <QuickAction icon={CalendarDays}  label="Meal Plan"       desc="View 7-day plan"       accent="#3b82f6" onClick={() => navigate('/meal-plan')}        dark={dark} />
      </div>
    </div>
  );
};

export default DashboardPage;