// src/pages/AnalyticsPage.jsx

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  BarChart2, Loader2, RefreshCw, Brain,
  TrendingUp, PieChart,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  generateProgressReport,
  getProgressReport,
  getLearnedPreferences,
} from '../api/analytics';
import { getMealLogs } from '../api/mealLogs';
import AdherenceChart from '../components/analytics/AdherenceChart';
import MacroPieChart from '../components/analytics/MacroPieChart';
import ProgressReportCard from '../components/analytics/ProgressReportCard';
import LearnedPreferencesCard from '../components/analytics/LearnedPreferencesCard';

const TABS = [
  { id: 'overview',    label: 'Overview',    icon: BarChart2  },
  { id: 'report',      label: 'AI Report',   icon: TrendingUp },
  { id: 'preferences', label: 'AI Learning', icon: Brain      },
];

// Last 7 days date range
const getLast7Days = () => {
  const to   = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 6);
  const fmt = (d) => d.toISOString().split('T')[0];
  return { dateFrom: fmt(from), dateTo: fmt(to) };
};

const AnalyticsPage = () => {
  const [activeTab, setActiveTab]   = useState('overview');
  const [generating, setGenerating] = useState(false);
  const { dateFrom, dateTo } = getLast7Days();

  // Meal logs for charts (last 7 days)
  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['mealLogs', 'analytics', dateFrom, dateTo],
    queryFn:  () => getMealLogs({ dateFrom, dateTo, limit: 100 }),
  });

  // Progress report
  const { data: reportData, isLoading: reportLoading, refetch: refetchReport } = useQuery({
    queryKey: ['progressReport'],
    queryFn:  getProgressReport,
    retry:    false,
  });

  // Learned preferences
  const { data: prefsData, isLoading: prefsLoading } = useQuery({
    queryKey: ['learnedPreferences'],
    queryFn:  getLearnedPreferences,
    retry:    false,
  });

  // Generate report mutation
  const reportMutation = useMutation({
    mutationFn: generateProgressReport,
    onMutate:   () => setGenerating(true),
    onSuccess:  () => {
      refetchReport();
      toast.success('Progress report generated!');
      setGenerating(false);
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Failed to generate report. Log some meals first.';
      toast.error(msg);
      setGenerating(false);
    },
  });

  const logs       = logsData?.logs || [];
  const report     = reportData;
  const hasReport  = report && (report.avg_adherence_pct !== undefined);

  // Build daily adherence data from logs
  const dailyMap = {};
  logs.forEach((log) => {
    if (!dailyMap[log.log_date]) {
      dailyMap[log.log_date] = {
        log_date:         log.log_date,
        actual_calories:  0,
        planned_calories: 2000, // fallback
        meals_logged:     0,
        meals_skipped:    0,
        protein_g:        0,
        carbs_g:          0,
        fat_g:            0,
      };
    }
    dailyMap[log.log_date].actual_calories  += log.calories  || 0;
    dailyMap[log.log_date].protein_g        += log.protein_g || 0;
    dailyMap[log.log_date].carbs_g          += log.carbs_g   || 0;
    dailyMap[log.log_date].fat_g            += log.fat_g     || 0;
    dailyMap[log.log_date].meals_logged     += 1;
  });

  const dailyLogs = Object.values(dailyMap).map((d) => ({
    ...d,
    adherence_pct: d.planned_calories
      ? (d.actual_calories / d.planned_calories) * 100
      : 0,
  }));

  return (
    <div className="p-6 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-50 rounded-lg">
          <BarChart2 className="text-primary-600" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500">Your nutrition progress at a glance</p>
        </div>
      </div>

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

      {/* ── TAB: Overview ── */}
      {activeTab === 'overview' && (
        <div className="space-y-5">

          {logsLoading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="animate-spin text-primary-600" size={26} />
            </div>
          ) : (
            <>
              {/* Calorie Adherence */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center gap-2 mb-1">
                  <TrendingUp size={16} className="text-primary-600" />
                  <h3 className="text-sm font-semibold text-gray-900">
                    Calorie Adherence — Last 7 Days
                  </h3>
                </div>
                <p className="text-xs text-gray-400 mb-4">
                  Green = ≥90% · Amber = 60–89% · Red = &lt;60%
                </p>
                <AdherenceChart logs={dailyLogs} />
              </div>

              {/* Macro Split */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <PieChart size={16} className="text-primary-600" />
                  <h3 className="text-sm font-semibold text-gray-900">
                    Macro Split — Last 7 Days
                  </h3>
                </div>
                <MacroPieChart logs={logs} />
              </div>

              {/* Quick stats */}
              {logs.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    {
                      label: 'Meals Logged',
                      value: logs.length,
                      unit: '',
                      color: 'text-primary-600',
                    },
                    {
                      label: 'Avg Daily Cals',
                      value: dailyLogs.length
                        ? Math.round(dailyLogs.reduce((s, d) => s + d.actual_calories, 0) / dailyLogs.length)
                        : 0,
                      unit: 'kcal',
                      color: 'text-amber-600',
                    },
                    {
                      label: 'Total Protein',
                      value: Math.round(logs.reduce((s, l) => s + (l.protein_g || 0), 0)),
                      unit: 'g',
                      color: 'text-blue-600',
                    },
                    {
                      label: 'Days Tracked',
                      value: dailyLogs.length,
                      unit: '/ 7',
                      color: 'text-green-600',
                    },
                  ].map(({ label, value, unit, color }) => (
                    <div key={label} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                      <p className={`text-2xl font-bold ${color}`}>
                        {value}
                        <span className="text-xs font-normal text-gray-400 ml-0.5">{unit}</span>
                      </p>
                      <p className="text-xs text-gray-500 mt-1">{label}</p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* ── TAB: AI Report ── */}
      {activeTab === 'report' && (
        <div className="space-y-5">

          {/* Generate button */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500">
              {hasReport
                ? `Report for week of ${report.week_start} – ${report.week_end}`
                : 'No report generated yet'}
            </p>
            <button
              onClick={() => reportMutation.mutate()}
              disabled={generating}
              className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors disabled:opacity-60"
            >
              {generating
                ? <><Loader2 size={14} className="animate-spin" /> Generating...</>
                : <><RefreshCw size={14} /> {hasReport ? 'Regenerate' : 'Generate Report'}</>
              }
            </button>
          </div>

          {reportLoading || generating ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="animate-spin text-primary-600" size={26} />
            </div>
          ) : hasReport ? (
            <ProgressReportCard report={report} />
          ) : (
            <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
              <TrendingUp size={40} className="mx-auto text-gray-200 mb-3" />
              <p className="text-gray-500 font-medium">No report yet</p>
              <p className="text-sm text-gray-400 mt-1">
                Log at least one meal, then generate your report
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: AI Learning ── */}
      {activeTab === 'preferences' && (
        <div className="space-y-5">
          <p className="text-sm text-gray-500">
            Every time you rate a recipe, the AI updates these preferences to personalise future recipes.
          </p>

          {prefsLoading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="animate-spin text-primary-600" size={26} />
            </div>
          ) : (
            <LearnedPreferencesCard preferences={prefsData} />
          )}
        </div>
      )}
    </div>
  );
};

export default AnalyticsPage;