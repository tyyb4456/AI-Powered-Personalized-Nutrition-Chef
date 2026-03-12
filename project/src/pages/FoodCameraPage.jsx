// src/pages/FoodCameraPage.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Loader2, RotateCcw, Sparkles, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { analyseImageBase64 } from '../api/images';
import { logMeal } from '../api/mealLogs';
import ImageDropzone from '../components/image/ImageDropzone';
import FoodAnalysisResult from '../components/image/FoodAnalysisResult';
import SelectField from '../components/ui/SelectField';
import { useForm } from 'react-hook-form';
import { useTheme } from '../store/ThemeContext';

const toISODate = (d) => d.toISOString().split('T')[0];

const MEAL_SLOT_OPTIONS = [
  { value: 'breakfast', label: 'Breakfast' },
  { value: 'lunch',     label: 'Lunch' },
  { value: 'dinner',    label: 'Dinner' },
  { value: 'snack',     label: 'Snack' },
];

const FoodCameraPage = () => {
  const { dark } = useTheme();
  const navigate    = useNavigate();
  const queryClient = useQueryClient();
  const [imageData, setImageData] = useState(null);
  const [result,    setResult]    = useState(null);
  const [analysing, setAnalysing] = useState(false);

  const { register, watch } = useForm({ defaultValues: { meal_slot: '' } });
  const mealSlot = watch('meal_slot');

  const analyseMutation = useMutation({
    mutationFn: analyseImageBase64,
    onSuccess: (data) => {
      setResult(data);
      setAnalysing(false);
      toast.success('Food identified!');
    },
    onError: (err) => {
      toast.error(err.response?.data?.detail || 'Analysis failed. Try a clearer photo.');
      setAnalysing(false);
    },
  });

  const logMutation = useMutation({
    mutationFn: logMeal,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mealLogs'] });
      queryClient.invalidateQueries({ queryKey: ['adherence'] });
      toast.success('Meal logged from photo!');
      navigate('/meal-log');
    },
    onError: () => toast.error('Failed to log meal'),
  });

  const handleAnalyse = () => {
    if (!imageData) return;
    setAnalysing(true);
    setResult(null);
    analyseMutation.mutate({ image_base64: imageData.base64, mime_type: imageData.mime_type, auto_log: false });
  };

  const handleLogThis = () => {
    if (!result) return;
    const nutrition = result.estimated_nutrition || {};
    logMutation.mutate({
      dish_name: result.dish_summary || 'Photo meal',
      meal_slot: mealSlot || result.meal_type_guess || 'lunch',
      calories:  nutrition.calories  || 0,
      protein_g: nutrition.protein_g || 0,
      carbs_g:   nutrition.carbs_g   || 0,
      fat_g:     nutrition.fat_g     || 0,
      log_date:  toISODate(new Date()),
      source:    'image',
    });
  };

  const handleReset = () => { setImageData(null); setResult(null); setAnalysing(false); };

  const text  = dark ? 'text-white' : 'text-gray-900';
  const muted = dark ? 'text-gray-500' : 'text-gray-400';
  const card  = dark ? 'bg-white/4 border-white/8' : 'bg-white border-black/8';
  const btnPrimary = dark
    ? 'bg-white text-black hover:bg-gray-100 disabled:opacity-30'
    : 'bg-gray-900 text-white hover:bg-black disabled:opacity-40';
  const btnGhost = dark
    ? 'border-white/10 text-gray-400 hover:border-white/20 hover:text-white'
    : 'border-black/10 text-gray-500 hover:border-black/20 hover:text-gray-900';

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
            <Camera size={15} className={text} />
          </div>
          <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>Food Camera</span>
        </div>
        <h1 className={`text-3xl font-bold tracking-tight ${text}`}>Snap & Identify</h1>
        <p className={`text-sm mt-1 ${muted}`}>Upload a food photo — AI will identify it and estimate nutrition</p>
      </div>

      <div className={`rounded-2xl border p-6 mb-4 ${card}`}>
        <ImageDropzone onImageReady={setImageData} dark={dark} />
      </div>

      {/* Meal slot */}
      {imageData && !result && (
        <div className={`rounded-2xl border p-6 mb-4 ${card}`}>
          <SelectField
            label="Meal Slot"
            name="meal_slot"
            register={register}
            options={MEAL_SLOT_OPTIONS}
            placeholder="Auto-detect"
          />
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 mb-6">
        {imageData && (
          <button
            onClick={handleAnalyse}
            disabled={analysing || logMutation.isPending}
            className={`flex-1 py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-200 ${btnPrimary}`}
          >
            {analysing ? <><Loader2 size={14} className="animate-spin" /> Analysing…</> : <><Sparkles size={14} /> Analyse Food</>}
          </button>
        )}
        {(imageData || result) && (
          <button
            onClick={handleReset}
            className={`px-4 py-3 rounded-xl text-sm border flex items-center gap-2 transition-all duration-200 ${btnGhost}`}
          >
            <RotateCcw size={13} /> Reset
          </button>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className={`rounded-2xl border p-6 ${card}`}>
          <FoodAnalysisResult result={result} onLogThis={handleLogThis} dark={dark} />
        </div>
      )}
    </div>
  );
};

export default FoodCameraPage;