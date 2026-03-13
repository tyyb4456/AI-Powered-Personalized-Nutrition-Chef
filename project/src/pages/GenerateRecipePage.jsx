// src/pages/GenerateRecipePage.jsx
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Sparkles, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { generateRecipe } from '../api/recipes';
import SelectField from '../components/ui/SelectField';
import RecipeDetail from '../components/recipe/RecipeDetail';
import { useTheme } from '../store/ThemeContext';
import { 
  Utensils, Flame, Sun, Moon, Apple, Coffee 
} from 'lucide-react';

const GenerateRecipePage = () => {
  const { dark } = useTheme();
  const [loading, setLoading] = useState(false);
  const [recipe, setRecipe] = useState(null);
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
      toast.error(err.response?.data?.detail || 'Generation failed. Make sure your profile is complete.');
    } finally {
      setLoading(false);
    }
  };

  const text    = dark ? 'text-white'   : 'text-gray-900';
  const muted   = dark ? 'text-gray-500' : 'text-gray-400';
  const card    = dark ? 'bg-white/4 border-white/8' : 'bg-white border-black/8';
  const skeletonBase = dark ? 'bg-white/6' : 'bg-gray-100';
  const skeletonShimmer = dark ? 'bg-white/4' : 'bg-gray-50';

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
            <Sparkles size={15} className={text} />
          </div>
          <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>AI Recipe</span>
        </div>
        <h1 className={`text-3xl font-bold tracking-tight ${text}`}>Generate Recipe</h1>
        <p className={`text-sm mt-1 ${muted}`}>AI will craft a recipe based on your health profile</p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* Override card */}
        <div className={`rounded-2xl border p-6 mb-4 ${card}`}>
          <p className={`text-sm font-semibold mb-1 ${text}`}>Override defaults</p>
          <p className={`text-xs mb-5 ${muted}`}>Leave blank to use your saved profile preferences</p>

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
    { value: 'mild',      label: (<span className="flex items-center gap-2"><Flame size={14}/> Mild</span>) },
    { value: 'medium',    label: (<span className="flex items-center gap-2"><Flame size={14}/> Medium</span>) },
    { value: 'hot',       label: (<span className="flex items-center gap-2"><Flame size={14}/> Hot</span>) },
    { value: 'extra_hot', label: (<span className="flex items-center gap-2"><Flame size={14}/> Extra Hot</span>) },
  ]}
  placeholder="From profile"
/>
<SelectField
  label="Meal Type"
  name="meal_type"
  register={register}
  options={[
    { value: 'breakfast', label: (<span className="flex items-center gap-2"><Coffee size={14}/> Breakfast</span>) },
    { value: 'lunch',     label: (<span className="flex items-center gap-2"><Sun size={14}/> Lunch</span>) },
    { value: 'dinner',    label: (<span className="flex items-center gap-2"><Moon size={14}/> Dinner</span>) },
    { value: 'snack',     label: (<span className="flex items-center gap-2"><Apple size={14}/> Snack</span>) },
  ]}
  placeholder="Any"
/>
          </div>
        </div>

        {/* Generate button */}
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-200 ${
            dark
              ? 'bg-white text-black hover:bg-gray-100 disabled:opacity-30'
              : 'bg-gray-900 text-white hover:bg-black disabled:opacity-40'
          }`}
        >
          {loading
            ? <><Loader2 size={15} className="animate-spin" /> Generating… (8–20 seconds)</>
            : <><Sparkles size={15} /> Generate Recipe</>
          }
        </button>
      </form>

      {/* Loading skeleton */}
      {loading && (
        <div className={`mt-4 rounded-2xl border p-6 animate-pulse space-y-4 ${card}`}>
          <div className={`h-5 rounded-lg w-2/3 ${skeletonBase}`} />
          <div className="flex gap-3">
            {[1,2,3,4,5].map(i => (
              <div key={i} className={`h-16 rounded-xl flex-1 ${skeletonShimmer}`} />
            ))}
          </div>
          <div className={`h-3 rounded-lg w-full ${skeletonBase}`} />
          <div className={`h-3 rounded-lg w-5/6 ${skeletonShimmer}`} />
          <div className={`h-3 rounded-lg w-4/6 ${skeletonBase}`} />
          <div className={`h-3 rounded-lg w-3/4 ${skeletonShimmer}`} />
        </div>
      )}

      {/* Result */}
      {recipe && !loading && (
        <div className="mt-4">
          <RecipeDetail recipe={recipe} />
        </div>
      )}
    </div>
  );
};

export default GenerateRecipePage;