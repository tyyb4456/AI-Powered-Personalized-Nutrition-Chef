// src/pages/GenerateRecipePage.jsx

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Sparkles, Loader2, ChefHat, RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import { generateRecipe } from '../api/recipes';
import SelectField from '../components/ui/SelectField';
import RecipeDetail from '../components/recipe/RecipeDetail';

const GenerateRecipePage = () => {
  const [loading, setLoading] = useState(false);
  const [recipe,  setRecipe]  = useState(null);
  const { register, handleSubmit } = useForm();

  const onSubmit = async (data) => {
    setLoading(true);
    setRecipe(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(data).filter(([, v]) => v !== '' && v !== undefined)
      );
      const result = await generateRecipe(payload);
      setRecipe(result);
      toast.success('Recipe generated!');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Generation failed. Make sure your profile is complete.';
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-50 rounded-lg">
            <Sparkles className="text-primary-600" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Generate Recipe</h1>
            <p className="text-sm text-gray-500">AI will craft a recipe based on your health profile</p>
          </div>
        </div>
        {recipe && (
          <button
            onClick={() => setRecipe(null)}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 hover:border-gray-300 px-3 py-1.5 rounded-lg transition-colors"
          >
            <RotateCcw size={13} />
            New recipe
          </button>
        )}
      </div>

      {/* Override Form — hidden after generation */}
      {!recipe && (
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="bg-white rounded-xl border border-gray-200 p-6 mb-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-1">Override defaults</h2>
            <p className="text-xs text-gray-400 mb-4">Leave blank to use your saved profile preferences</p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <SelectField
                label="Cuisine"
                name="cuisine"
                register={register}
                options={[
                  { value: 'pakistani',     label: '🇵🇰 Pakistani' },
                  { value: 'indian',        label: '🇮🇳 Indian' },
                  { value: 'mediterranean', label: '🫒 Mediterranean' },
                  { value: 'chinese',       label: '🇨🇳 Chinese' },
                  { value: 'italian',       label: '🇮🇹 Italian' },
                  { value: 'american',      label: '🇺🇸 American' },
                ]}
                placeholder="From profile"
              />
              <SelectField
                label="Spice Level"
                name="spice_level"
                register={register}
                options={[
                  { value: 'mild',      label: '🟢 Mild' },
                  { value: 'medium',    label: '🟡 Medium' },
                  { value: 'hot',       label: '🔴 Hot' },
                  { value: 'extra_hot', label: '🌶️ Extra Hot' },
                ]}
                placeholder="From profile"
              />
              <SelectField
                label="Meal Type"
                name="meal_type"
                register={register}
                options={[
                  { value: 'breakfast', label: '🌅 Breakfast' },
                  { value: 'lunch',     label: '☀️ Lunch' },
                  { value: 'dinner',    label: '🌙 Dinner' },
                  { value: 'snack',     label: '🍎 Snack' },
                ]}
                placeholder="Any"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white font-semibold py-3.5 rounded-xl text-sm transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Crafting your recipe…
              </>
            ) : (
              <>
                <ChefHat size={16} />
                Generate Recipe
              </>
            )}
          </button>
        </form>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="mt-6 space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-2/3 mb-3" />
              <div className="h-3 bg-gray-100 rounded w-full mb-2" />
              <div className="h-3 bg-gray-100 rounded w-4/5" />
            </div>
          ))}
        </div>
      )}

      {/* Recipe — RecipeDetail owns all follow-up chat logic */}
      {recipe && !loading && (
        <RecipeDetail
          recipe={recipe}
          onRecipeUpdate={setRecipe}
        />
      )}

    </div>
  );
};

export default GenerateRecipePage;