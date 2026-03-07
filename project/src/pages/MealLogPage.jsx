// src/pages/MealLogPage.jsx

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ClipboardList, ChevronLeft, ChevronRight, Loader2, UtensilsCrossed } from 'lucide-react';
import toast from 'react-hot-toast';
import { logMeal, getMealLogs, deleteMealLog } from '../api/mealLogs';
import LogMealForm from '../components/meallog/LogMealForm';
import LogEntry from '../components/meallog/LogEntry';
import DailyProgress from '../components/meallog/DailyProgress';

// Format date as YYYY-MM-DD
const toISODate = (date) => date.toISOString().split('T')[0];

const formatDisplay = (isoDate) => {
  const d = new Date(isoDate + 'T00:00:00');
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
};

const MealLogPage = () => {
  const [selectedDate, setSelectedDate] = useState(toISODate(new Date()));
  const [showForm, setShowForm]         = useState(false);
  const queryClient = useQueryClient();

  // Fetch logs for selected date
  const { data, isLoading } = useQuery({
    queryKey: ['mealLogs', selectedDate],
    queryFn: () => getMealLogs({ dateFrom: selectedDate, dateTo: selectedDate }),
  });

  const logs = data?.logs || [];

  // Log meal mutation
  const logMutation = useMutation({
    mutationFn: logMeal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mealLogs', selectedDate] });
      queryClient.invalidateQueries({ queryKey: ['adherence',  selectedDate] });
      toast.success('Meal logged!');
      setShowForm(false);
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Failed to log meal.';
      toast.error(msg);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteMealLog,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mealLogs', selectedDate] });
      queryClient.invalidateQueries({ queryKey: ['adherence',  selectedDate] });
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

  return (
    <div className="p-6 max-w-3xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-50 rounded-lg">
          <ClipboardList className="text-primary-600" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Meal Log</h1>
          <p className="text-sm text-gray-500">Track what you actually eat</p>
        </div>
      </div>

      {/* Date Navigator */}
      <div className="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-4 py-3 mb-5">
        <button
          onClick={() => changeDate(-1)}
          className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ChevronLeft size={18} className="text-gray-600" />
        </button>

        <div className="text-center">
          <p className="text-sm font-semibold text-gray-900">{formatDisplay(selectedDate)}</p>
          {isToday && (
            <span className="text-xs text-primary-600 font-medium">Today</span>
          )}
        </div>

        <button
          onClick={() => changeDate(1)}
          disabled={isToday}
          className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-30"
        >
          <ChevronRight size={18} className="text-gray-600" />
        </button>
      </div>

      {/* Daily Progress */}
      <div className="mb-5">
        <DailyProgress date={selectedDate} />
      </div>

      {/* Log entries */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-900">
            Meals Logged
            {logs.length > 0 && (
              <span className="ml-2 text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                {logs.length}
              </span>
            )}
          </h2>
          <button
            onClick={() => setShowForm(!showForm)}
            className="text-sm text-primary-600 font-medium hover:underline"
          >
            {showForm ? 'Cancel' : '+ Add Meal'}
          </button>
        </div>

        {/* Inline form */}
        {showForm && (
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 mb-4">
            <LogMealForm
              date={selectedDate}
              onSuccess={(data) => logMutation.mutateAsync(data)}
            />
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center h-24">
            <Loader2 className="animate-spin text-primary-600" size={22} />
          </div>
        )}

        {/* Empty */}
        {!isLoading && logs.length === 0 && !showForm && (
          <div className="text-center py-10">
            <UtensilsCrossed size={32} className="mx-auto text-gray-200 mb-2" />
            <p className="text-sm text-gray-400">No meals logged for this day</p>
            <button
              onClick={() => setShowForm(true)}
              className="mt-3 text-sm text-primary-600 font-medium hover:underline"
            >
              Log your first meal
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

      {/* Daily macro summary */}
      {logs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Daily Totals</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Calories', value: logs.reduce((s, l) => s + (l.calories  || 0), 0), unit: 'kcal', color: 'text-amber-600'  },
              { label: 'Protein',  value: logs.reduce((s, l) => s + (l.protein_g || 0), 0), unit: 'g',    color: 'text-blue-600'   },
              { label: 'Carbs',    value: logs.reduce((s, l) => s + (l.carbs_g   || 0), 0), unit: 'g',    color: 'text-orange-600' },
              { label: 'Fat',      value: logs.reduce((s, l) => s + (l.fat_g     || 0), 0), unit: 'g',    color: 'text-purple-600' },
            ].map(({ label, value, unit, color }) => (
              <div key={label} className="bg-gray-50 rounded-xl p-3 text-center">
                <p className={`text-xl font-bold ${color}`}>
                  {typeof value === 'number' ? value.toFixed(value % 1 === 0 ? 0 : 1) : '—'}
                  <span className="text-xs font-normal text-gray-400 ml-0.5">{unit}</span>
                </p>
                <p className="text-xs text-gray-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MealLogPage;