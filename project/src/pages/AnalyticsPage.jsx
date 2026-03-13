// src/pages/AnalyticsPage.jsx
import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { BarChart2, Loader2, RefreshCw, Brain, TrendingUp, PieChart } from 'lucide-react';
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
import { useTheme } from '../store/ThemeContext';

const TABS = [
  { id: 'overview',    label: 'Overview',    icon: BarChart2  },
  { id: 'report',      label: 'AI Report',   icon: TrendingUp },
  { id: 'preferences', label: 'AI Learning', icon: Brain      },
];

const getLast7Days = () => {
  const to   = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 6);
  const fmt = (d) => d.toISOString().split('T')[0];
  return { dateFrom: fmt(from), dateTo: fmt(to) };
};

const AnalyticsPage = () => {
  const { dark } = useTheme();
  const [activeTab, setActiveTab]   = useState('overview');
  const [generating, setGenerating] = useState(false);
  const { dateFrom, dateTo } = getLast7Days();

  const { data: logsData, isLoading: logsLoading } = useQuery({
    queryKey: ['mealLogs', 'analytics', dateFrom, dateTo],
    queryFn:  () => getMealLogs({ dateFrom, dateTo, limit: 100 }),
  });

  const { data: reportData, isLoading: reportLoading, refetch: refetchReport } = useQuery({
    queryKey: ['progressReport'],
    queryFn:  getProgressReport,
    retry:    false,
  });

  const { data: prefsData, isLoading: prefsLoading } = useQuery({
    queryKey: ['learnedPreferences'],
    queryFn:  getLearnedPreferences,
    retry:    false,
  });

  const reportMutation = useMutation({
    mutationFn: generateProgressReport,
    onMutate:   () => setGenerating(true),
    onSuccess:  () => {
      refetchReport();
      toast.success('Progress report generated!');
      setGenerating(false);
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Failed to generate report. Log some meals first.');
      setGenerating(false);
    },
  });

  const logs      = logsData?.logs || [];
  const report    = reportData;
  const hasReport = report && report.avg_adherence_pct !== undefined;

  // Build daily adherence data
  const dailyMap = {};
  logs.forEach((log) => {
    if (!dailyMap[log.log_date]) {
      dailyMap[log.log_date] = {
        log_date: log.log_date,
        actual_calories: 0, planned_calories: 2000,
        meals_logged: 0, meals_skipped: 0,
        protein_g: 0, carbs_g: 0, fat_g: 0,
      };
    }
    dailyMap[log.log_date].actual_calories += log.calories  || 0;
    dailyMap[log.log_date].protein_g       += log.protein_g || 0;
    dailyMap[log.log_date].carbs_g         += log.carbs_g   || 0;
    dailyMap[log.log_date].fat_g           += log.fat_g     || 0;
    dailyMap[log.log_date].meals_logged    += 1;
  });
  const dailyLogs = Object.values(dailyMap).map((d) => ({
    ...d,
    adherence_pct: d.planned_calories ? (d.actual_calories / d.planned_calories) * 100 : 0,
  }));

  // Theme tokens
  const text    = dark ? 'text-white'    : 'text-gray-900';
  const muted   = dark ? 'text-gray-500' : 'text-gray-400';
  const subtext = dark ? 'text-gray-400' : 'text-gray-500';
  const card    = dark ? 'bg-white/4 border-white/8'  : 'bg-white border-black/8';
  const tabBar  = dark ? 'bg-white/5'                 : 'bg-black/5';
  const tabActive = dark
    ? 'bg-white/10 text-white'
    : 'bg-white text-gray-900 shadow-sm';
  const tabIdle = dark
    ? 'text-gray-500 hover:text-gray-300'
    : 'text-gray-500 hover:text-gray-700';
  const genBtn  = dark
    ? 'bg-white text-black hover:bg-gray-100 disabled:opacity-30'
    : 'bg-gray-900 text-white hover:bg-black disabled:opacity-40';
  const emptyCard = dark ? 'bg-white/3 border-white/6' : 'bg-gray-50 border-black/6';
  const statCell  = dark ? 'bg-white/6' : 'bg-gray-50';
  const sectionLabel = `text-xs font-semibold tracking-widest uppercase mb-1 flex items-center gap-2 ${muted}`;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
            <BarChart2 size={15} className={text} />
          </div>
          <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>Analytics</span>
        </div>
        <h1 className={`text-3xl font-bold tracking-tight ${text}`}>Nutrition Progress</h1>
        <p className={`text-sm mt-1 ${muted}`}>Your nutrition progress at a glance</p>
      </div>

      {/* Tabs */}
      <div className={`flex gap-1 p-1 rounded-2xl mb-6 w-fit ${tabBar}`}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl transition-all duration-200 ${
              activeTab === id ? tabActive : tabIdle
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* ── TAB: Overview ── */}
      {activeTab === 'overview' && (
        <div className="space-y-4">
          {logsLoading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className={`animate-spin ${dark ? 'text-white/30' : 'text-gray-300'}`} size={24} />
            </div>
          ) : (
            <>
              {/* Calorie Adherence */}
              <div className={`rounded-2xl border p-5 ${card}`}>
                <div className={`${sectionLabel}`}>
                  <TrendingUp size={13} /> Calorie Adherence — Last 7 Days
                </div>
                <p className={`text-xs mb-4 ${dark ? 'text-gray-600' : 'text-gray-400'}`}>
                  Green = ≥90% · Amber = 60–89% · Red = &lt;60%
                </p>
                <AdherenceChart logs={dailyLogs} />
              </div>

              {/* Macro Split */}
              <div className={`rounded-2xl border p-5 ${card}`}>
                <div className={sectionLabel}>
                  <PieChart size={13} /> Macro Split — Last 7 Days
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
                      color: 'text-blue-400',
                    },
                    {
                      label: 'Avg Daily Cals',
                      value: dailyLogs.length
                        ? Math.round(dailyLogs.reduce((s, d) => s + d.actual_calories, 0) / dailyLogs.length)
                        : 0,
                      unit: 'kcal',
                      color: 'text-amber-400',
                    },
                    {
                      label: 'Total Protein',
                      value: Math.round(logs.reduce((s, l) => s + (l.protein_g || 0), 0)),
                      unit: 'g',
                      color: 'text-green-400',
                    },
                    {
                      label: 'Days Tracked',
                      value: dailyLogs.length,
                      unit: '',
                      color: 'text-purple-400',
                    },
                  ].map(({ label, value, unit, color }) => (
                    <div key={label} className={`rounded-2xl border p-4 text-center ${card}`}>
                      <p className={`text-2xl font-bold ${color}`}>
                        {value}
                        {unit && <span className={`text-xs font-normal ml-0.5 ${muted}`}>{unit}</span>}
                      </p>
                      <p className={`text-xs mt-0.5 ${muted}`}>{label}</p>
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
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className={`text-sm ${subtext}`}>
              AI-generated summary of your nutrition adherence and trends.
            </p>
            <button
              onClick={() => reportMutation.mutate()}
              disabled={generating || reportLoading}
              className={`flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all duration-200 ${genBtn}`}
            >
              {generating
                ? <><Loader2 size={13} className="animate-spin" /> Generating...</>
                : <><RefreshCw size={13} /> {hasReport ? 'Regenerate' : 'Generate Report'}</>
              }
            </button>
          </div>

          {reportLoading || generating ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className={`animate-spin ${dark ? 'text-white/30' : 'text-gray-300'}`} size={24} />
            </div>
          ) : hasReport ? (
            <ProgressReportCard report={report} />
          ) : (
            <div className={`text-center py-16 rounded-2xl border ${emptyCard}`}>
              <div className={`inline-flex p-4 rounded-2xl mb-3 ${dark ? 'bg-white/5' : 'bg-black/4'}`}>
                <TrendingUp size={28} className={muted} />
              </div>
              <p className={`font-semibold mb-1 ${text}`}>No report yet</p>
              <p className={`text-sm ${muted}`}>Log at least one meal, then generate your report</p>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: AI Learning ── */}
      {activeTab === 'preferences' && (
        <div className="space-y-4">
          <p className={`text-sm ${subtext}`}>
            Every time you rate a recipe, the AI updates these preferences to personalise future recipes.
          </p>
          {prefsLoading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className={`animate-spin ${dark ? 'text-white/30' : 'text-gray-300'}`} size={24} />
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