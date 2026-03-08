// src/components/analytics/LearnedPreferencesCard.jsx

import { useState } from 'react';
import { Brain, RotateCcw, Loader2, CheckCircle } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { resetLearnedPreferences } from '../../api/analytics';
import toast from 'react-hot-toast';

const PreferenceRow = ({ label, value }) => {
  if (!value || (Array.isArray(value) && value.length === 0)) return null;

  const display = Array.isArray(value) ? value.join(', ') : String(value);

  return (
    <div className="flex items-start justify-between text-sm py-2 border-b border-gray-50 last:border-0">
      <span className="text-gray-500 capitalize">{label.replace(/_/g, ' ')}</span>
      <span className="text-gray-800 font-medium text-right max-w-[60%]">{display}</span>
    </div>
  );
};

const LearnedPreferencesCard = ({ preferences }) => {
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

  const prefs = preferences?.preferences || preferences || {};
  const hasPrefs = Object.keys(prefs).filter(k => prefs[k] && prefs[k] !== '' && !(Array.isArray(prefs[k]) && prefs[k].length === 0)).length > 0;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Brain size={17} className="text-primary-600" />
          <h3 className="text-sm font-semibold text-gray-900">Learned Preferences</h3>
        </div>

        {hasPrefs && (
          confirming ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Sure?</span>
              <button
                onClick={() => resetMutation.mutate()}
                disabled={resetMutation.isPending}
                className="text-xs text-red-600 font-medium hover:underline"
              >
                {resetMutation.isPending ? 'Resetting...' : 'Yes, reset'}
              </button>
              <button
                onClick={() => setConfirming(false)}
                className="text-xs text-gray-400 hover:underline"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirming(true)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              <RotateCcw size={12} />
              Reset
            </button>
          )
        )}
      </div>

      {!hasPrefs ? (
        <div className="text-center py-6">
          <Brain size={28} className="mx-auto text-gray-200 mb-2" />
          <p className="text-sm text-gray-400">No learned preferences yet</p>
          <p className="text-xs text-gray-300 mt-1">
            Rate recipes to help the AI learn your taste
          </p>
        </div>
      ) : (
        <div className="space-y-0">
          {Object.entries(prefs).map(([key, val]) => (
            <PreferenceRow key={key} label={key} value={val} />
          ))}
        </div>
      )}
    </div>
  );
};

export default LearnedPreferencesCard;