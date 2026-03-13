// src/components/analytics/LearnedPreferencesCard.jsx
import { useState } from 'react';
import { Brain, RotateCcw } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resetLearnedPreferences } from '../../api/analytics';
import { useTheme } from '../../store/ThemeContext';
import toast from 'react-hot-toast';

const PreferenceRow = ({ label, value, dark, divider }) => {
  if (!value || (Array.isArray(value) && value.length === 0)) return null;
  const display = Array.isArray(value) ? value.join(', ') : String(value);

  return (
    <div className={`flex items-start justify-between text-sm py-3 border-b last:border-0 ${divider}`}>
      <span className={`capitalize ${dark ? 'text-gray-500' : 'text-gray-500'}`}>
        {label.replace(/_/g, ' ')}
      </span>
      <span className={`font-medium text-right max-w-[60%] ${dark ? 'text-gray-200' : 'text-gray-800'}`}>
        {display}
      </span>
    </div>
  );
};

const LearnedPreferencesCard = ({ preferences }) => {
  const { dark } = useTheme();
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);

  const resetMutation = useMutation({
    mutationFn: resetLearnedPreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learnedPreferences'] });
      toast.success('Preferences reset — AI starts fresh');
      setConfirming(false);
    },
    onError: () => {
      toast.error('Failed to reset preferences');
      setConfirming(false);
    },
  });

  const prefs    = preferences?.preferences || preferences || {};
  const hasPrefs = Object.keys(prefs).filter(k =>
    prefs[k] && prefs[k] !== '' && !(Array.isArray(prefs[k]) && prefs[k].length === 0)
  ).length > 0;

  // Theme tokens
  const card    = dark ? 'bg-white/4 border-white/8'  : 'bg-white border-black/8';
  const muted   = dark ? 'text-gray-500' : 'text-gray-400';
  const divider = dark ? 'border-white/6' : 'border-black/5';
  const text    = dark ? 'text-white'    : 'text-gray-900';
  const resetIdle = dark
    ? 'text-gray-600 hover:text-red-400'
    : 'text-gray-400 hover:text-red-500';

  return (
    <div className={`rounded-2xl border p-5 ${card}`}>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain size={14} className={muted} />
          <span className={`text-xs font-semibold tracking-widest uppercase ${muted}`}>
            Learned Preferences
          </span>
        </div>

        {hasPrefs && (
          confirming ? (
            <div className="flex items-center gap-2">
              <span className={`text-xs ${muted}`}>Sure?</span>
              <button
                onClick={() => resetMutation.mutate()}
                disabled={resetMutation.isPending}
                className="text-xs text-red-400 font-semibold hover:text-red-300 transition-colors"
              >
                {resetMutation.isPending ? 'Resetting...' : 'Yes, reset'}
              </button>
              <button
                onClick={() => setConfirming(false)}
                className={`text-xs transition-colors ${muted} hover:${text}`}
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirming(true)}
              className={`flex items-center gap-1 text-xs transition-colors ${resetIdle}`}
            >
              <RotateCcw size={11} />
              Reset
            </button>
          )
        )}
      </div>

      {/* Content */}
      {!hasPrefs ? (
        <div className="text-center py-8">
          <div className={`inline-flex p-3 rounded-2xl mb-3 ${dark ? 'bg-white/5' : 'bg-black/4'}`}>
            <Brain size={22} className={muted} />
          </div>
          <p className={`text-sm font-medium mb-1 ${dark ? 'text-gray-400' : 'text-gray-500'}`}>
            No learned preferences yet
          </p>
          <p className={`text-xs ${dark ? 'text-gray-600' : 'text-gray-400'}`}>
            Rate recipes to help the AI learn your taste
          </p>
        </div>
      ) : (
        <div>
          {Object.entries(prefs).map(([key, val]) => (
            <PreferenceRow key={key} label={key} value={val} dark={dark} divider={divider} />
          ))}
        </div>
      )}
    </div>
  );
};

export default LearnedPreferencesCard;