// src/pages/FoodCameraPage.jsx

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Loader2, RotateCcw, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { analyseImageBase64 } from '../api/images';
import { logMeal } from '../api/mealLogs';
import ImageDropzone from '../components/image/ImageDropzone';
import FoodAnalysisResult from '../components/image/FoodAnalysisResult';
import SelectField from '../components/ui/SelectField';
import { useForm } from 'react-hook-form';

// Today as YYYY-MM-DD
const toISODate = (d) => d.toISOString().split('T')[0];

const FoodCameraPage = () => {
  const navigate    = useNavigate();
  const queryClient = useQueryClient();
  const [imageData, setImageData] = useState(null);   // { base64, mime_type, dataUrl }
  const [result,    setResult]    = useState(null);
  const [analysing, setAnalysing] = useState(false);

  const { register, watch } = useForm({ defaultValues: { meal_slot: '' } });
  const mealSlot = watch('meal_slot');

  // Analyse mutation
  const analyseMutation = useMutation({
    mutationFn: analyseImageBase64,
    onSuccess: (data) => {
      setResult(data);
      setAnalysing(false);
      toast.success('Food identified!');
    },
    onError: (err) => {
      const msg = err.response?.data?.detail || 'Analysis failed. Try a clearer photo.';
      toast.error(msg);
      setAnalysing(false);
    },
  });

  // Log meal mutation
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
    analyseMutation.mutate({
      image_base64: imageData.base64,
      mime_type:    imageData.mime_type,
      auto_log:     false,
    });
  };

  const handleLogThis = () => {
    if (!result) return;
    const nutrition = result.estimated_nutrition || {};
    const today     = toISODate(new Date());

    logMutation.mutate({
      dish_name: result.dish_summary || 'Photo meal',
      meal_slot: mealSlot || result.meal_type_guess || 'lunch',
      calories:  nutrition.calories  || 0,
      protein_g: nutrition.protein_g || 0,
      carbs_g:   nutrition.carbs_g   || 0,
      fat_g:     nutrition.fat_g     || 0,
      log_date:  today,
      source:    'image',
    });
  };

  const handleReset = () => {
    setImageData(null);
    setResult(null);
    setAnalysing(false);
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-50 rounded-lg">
          <Camera className="text-primary-600" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Food Camera</h1>
          <p className="text-sm text-gray-500">
            Snap a photo — AI identifies the food and estimates nutrition
          </p>
        </div>
      </div>

      {/* Step 1 — Upload */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
        <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
          Step 1 — Upload Photo
        </p>
        <ImageDropzone
          onImageReady={setImageData}
          disabled={analysing}
        />
      </div>

      {/* Step 2 — Optional meal slot override */}
      {imageData && !result && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
          <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-3">
            Step 2 — Meal Slot <span className="text-gray-300 normal-case font-normal">(optional)</span>
          </p>
          <SelectField
            label="Override meal type"
            name="meal_slot"
            register={register}
            options={[
              { value: 'breakfast', label: '🌅 Breakfast' },
              { value: 'lunch',     label: '☀️ Lunch'     },
              { value: 'dinner',    label: '🌙 Dinner'    },
              { value: 'snack',     label: '🍎 Snack'     },
            ]}
            placeholder="Let AI detect"
          />
        </div>
      )}

      {/* Analyse button */}
      {imageData && !result && (
        <button
          onClick={handleAnalyse}
          disabled={analysing}
          className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3.5 rounded-xl text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2 mb-4"
        >
          {analysing ? (
            <>
              <Loader2 size={17} className="animate-spin" />
              Analysing your photo... (3–8 seconds)
            </>
          ) : (
            <>
              <Sparkles size={17} />
              Analyse Food
            </>
          )}
        </button>
      )}

      {/* Analysing skeleton */}
      {analysing && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse space-y-4 mb-4">
          <div className="h-5 bg-gray-200 rounded w-1/2" />
          <div className="flex gap-3">
            {[1,2,3,4,5].map(i => (
              <div key={i} className="h-16 bg-gray-100 rounded-xl flex-1" />
            ))}
          </div>
          <div className="h-4 bg-gray-100 rounded w-full" />
          <div className="h-4 bg-gray-100 rounded w-4/5" />
        </div>
      )}

      {/* Step 3 — Results */}
      {result && !analysing && (
        <>
          <div className="bg-white rounded-xl border border-gray-200 p-5 mb-4">
            <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-4">
              Step 3 — Results
            </p>
            <FoodAnalysisResult
              result={result}
              onLogThis={handleLogThis}
            />
          </div>

          {/* Start over */}
          <button
            onClick={handleReset}
            className="w-full flex items-center justify-center gap-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 bg-white hover:bg-gray-50 py-2.5 rounded-xl transition-colors"
          >
            <RotateCcw size={14} />
            Analyse another photo
          </button>
        </>
      )}

      {/* Logging in progress */}
      {logMutation.isPending && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl px-8 py-6 flex items-center gap-3 shadow-xl">
            <Loader2 className="animate-spin text-primary-600" size={22} />
            <span className="text-sm font-medium text-gray-700">Logging meal...</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default FoodCameraPage;