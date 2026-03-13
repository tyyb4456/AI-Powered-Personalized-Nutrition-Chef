// src/pages/MealLogPage.jsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ClipboardList, ChevronLeft, ChevronRight, Loader2, UtensilsCrossed, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { logMeal, getMealLogs, deleteMealLog } from '../api/mealLogs';
import LogMealForm from '../components/meallog/LogMealForm';
import LogEntry from '../components/meallog/LogEntry';
import DailyProgress from '../components/meallog/DailyProgress';
import { useTheme } from '../store/ThemeContext';

const toISODate    = (date)    => date.toISOString().split('T')[0];
const formatDisplay = (isoDate) => {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
};

const MealLogPage = () => {
  const { dark } = useTheme();
  const [selectedDate, setSelectedDate] = useState(toISODate(new Date()));
  const [showForm, setShowForm]         = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['mealLogs', selectedDate],
    queryFn: () => getMealLogs({ dateFrom: selectedDate, dateTo: selectedDate }),
  });

  const logs = data?.logs || [];

  const logMutation = useMutation({
    mutationFn: logMeal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mealLogs', selectedDate] });
      queryClient.invalidateQueries({ queryKey: ['adherence', selectedDate] });
      toast.success('Meal logged!');
      setShowForm(false);
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to log meal.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteMealLog,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mealLogs', selectedDate] });
      queryClient.invalidateQueries({ queryKey: ['adherence', selectedDate] });
      toast.success('Log deleted');
    },
    onError: () => toast.error('Failed to delete log'),
  });

  const changeDate = (delta) => {
    const d = new Date(selectedDate + 'T00:00:00');
    d.setDate(d.getDate() + delta);
    setSelectedDate(toISODate(d));
    setShowForm(false);
  };

  const isToday = selectedDate === toISODate(new Date());

  // Theme tokens
  const text    = dark ? 'text-white'    : 'text-gray-900';
  const muted   = dark ? 'text-gray-500' : 'text-gray-400';
  const subtext = dark ? 'text-gray-300' : 'text-gray-600';
  const card    = dark ? 'bg-white/4 border-white/8'  : 'bg-white border-black/8';
  const divider = dark ? 'border-white/6'              : 'border-black/5';
  const navBtn  = dark
    ? 'hover:bg-white/6 text-gray-400 hover:text-white disabled:opacity-20'
    : 'hover:bg-black/5 text-gray-500 hover:text-gray-900 disabled:opacity-30';
  const addBtn  = dark
    ? 'bg-white text-black hover:bg-gray-100'
    : 'bg-gray-900 text-white hover:bg-black';
  const cancelBtn = dark
    ? 'text-gray-400 hover:text-white'
    : 'text-gray-500 hover:text-gray-700';
  const formBg  = dark ? 'bg-white/3 border-white/8'  : 'bg-gray-50 border-black/6';
  const macroCell = dark ? 'bg-white/6' : 'bg-gray-50';
  const logFirstBtn = dark
    ? 'text-gray-400 hover:text-white'
    : 'text-gray-500 hover:text-gray-700';
  const todayBadge = dark
    ? 'bg-white/8 text-gray-300'
    : 'bg-black/5 text-gray-500';

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
            <ClipboardList size={15} className={text} />
          </div>
          <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>Meal Log</span>
        </div>
        <h1 className={`text-3xl font-bold tracking-tight ${text}`}>Track Your Meals</h1>
        <p className={`text-sm mt-1 ${muted}`}>Log what you actually eat each day</p>
      </div>

      {/* Date Navigator */}
      <div className={`flex items-center justify-between rounded-2xl border px-4 py-3 mb-4 ${card}`}>
        <button
          onClick={() => changeDate(-1)}
          className={`p-1.5 rounded-xl transition-all duration-200 ${navBtn}`}
        >
          <ChevronLeft size={18} />
        </button>
        <div className="text-center">
          <p className={`text-sm font-semibold ${text}`}>{formatDisplay(selectedDate)}</p>
          {isToday && (
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full mt-0.5 inline-block ${todayBadge}`}>
              Today
            </span>
          )}
        </div>
        <button
          onClick={() => changeDate(1)}
          disabled={isToday}
          className={`p-1.5 rounded-xl transition-all duration-200 ${navBtn}`}
        >
          <ChevronRight size={18} />
        </button>
      </div>

      {/* Daily Progress */}
      <div className="mb-4">
        <DailyProgress date={selectedDate} />
      </div>

      {/* Log entries card */}
      <div className={`rounded-2xl border p-5 mb-4 ${card}`}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold tracking-widest uppercase ${muted}`}>Meals Logged</span>
            {logs.length > 0 && (
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${dark ? 'bg-white/8 text-gray-400' : 'bg-black/5 text-gray-500'}`}>
                {logs.length}
              </span>
            )}
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className={`flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-xl transition-all duration-200 ${
              showForm ? cancelBtn : addBtn
            }`}
          >
            {showForm ? 'Cancel' : <><Plus size={13} /> Add Meal</>}
          </button>
        </div>

        {/* Inline form */}
        {showForm && (
          <div className={`rounded-xl border p-4 mb-4 ${formBg}`}>
            <LogMealForm
              date={selectedDate}
              onSuccess={(data) => logMutation.mutateAsync(data)}
            />
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <Loader2 className={`animate-spin ${dark ? 'text-white/30' : 'text-gray-300'}`} size={22} />
          </div>
        )}

        {/* Empty */}
        {!isLoading && logs.length === 0 && !showForm && (
          <div className="text-center py-10">
            <div className={`inline-flex p-3 rounded-2xl mb-3 ${dark ? 'bg-white/5' : 'bg-black/4'}`}>
              <UtensilsCrossed size={24} className={muted} />
            </div>
            <p className={`text-sm mb-1 ${subtext}`}>No meals logged for this day</p>
            <button
              onClick={() => setShowForm(true)}
              className={`text-sm font-semibold mt-2 transition-colors ${logFirstBtn}`}
            >
              Log your first meal →
            </button>
          </div>
        )}

        {/* List */}
        {!isLoading && logs.length > 0 && (
          <div className="space-y-2">
            {logs.map((log) => (
              <LogEntry
                key={log.log_id}
                log={log}
                onDelete={(id) => deleteMutation.mutate(id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Daily Totals */}
      {logs.length > 0 && (
        <div className={`rounded-2xl border p-5 ${card}`}>
          <span className={`text-xs font-semibold tracking-widest uppercase mb-4 block ${muted}`}>Daily Totals</span>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Calories', value: logs.reduce((s, l) => s + (l.calories  || 0), 0), unit: 'kcal', color: 'text-amber-400'  },
              { label: 'Protein',  value: logs.reduce((s, l) => s + (l.protein_g || 0), 0), unit: 'g',    color: 'text-blue-400'   },
              { label: 'Carbs',    value: logs.reduce((s, l) => s + (l.carbs_g   || 0), 0), unit: 'g',    color: 'text-orange-400' },
              { label: 'Fat',      value: logs.reduce((s, l) => s + (l.fat_g     || 0), 0), unit: 'g',    color: 'text-purple-400' },
            ].map(({ label, value, unit, color }) => (
              <div key={label} className={`rounded-xl p-3 text-center ${macroCell}`}>
                <p className={`text-xl font-bold ${color}`}>
                  {typeof value === 'number' ? value.toFixed(value % 1 === 0 ? 0 : 1) : '—'}
                  <span className={`text-xs font-normal ml-0.5 ${muted}`}>{unit}</span>
                </p>
                <p className={`text-xs mt-0.5 ${muted}`}>{label}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MealLogPage;