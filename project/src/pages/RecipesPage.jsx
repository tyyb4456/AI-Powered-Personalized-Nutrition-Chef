// src/pages/RecipesPage.jsx
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Loader2, ChefHat, Plus, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { listRecipes, getRecipeById } from '../api/recipes';
import RecipeCard from '../components/recipe/RecipeCard';
import RecipeDetail from '../components/recipe/RecipeDetail';
import { useTheme } from '../store/ThemeContext';
import toast from 'react-hot-toast';

const RecipesPage = () => {
  const { dark } = useTheme();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['recipes', page],
    queryFn: () => listRecipes({ page, limit: 12 }),
  });

  const recipes    = data?.recipes || [];
  const total      = data?.total || 0;
  const totalPages = Math.ceil(total / 12);

  const handleCardClick = async (recipe) => {
    setDetailLoading(true);
    try {
      const full = await getRecipeById(recipe.recipe_id);
      setSelected(full);
    } catch {
      toast.error('Failed to load recipe details.');
    } finally {
      setDetailLoading(false);
    }
  };

  // Theme tokens
  const text    = dark ? 'text-white'    : 'text-gray-900';
  const muted   = dark ? 'text-gray-500' : 'text-gray-400';
  const backBtn = dark
    ? 'text-gray-400 hover:text-white border-white/8 hover:border-white/20 hover:bg-white/5'
    : 'text-gray-500 hover:text-gray-900 border-black/10 hover:border-black/20 hover:bg-black/4';
  const pageBtn = dark
    ? 'border-white/10 text-gray-400 hover:text-white hover:border-white/20 disabled:opacity-20'
    : 'border-black/10 text-gray-500 hover:text-gray-900 hover:border-black/20 disabled:opacity-30';
  const genBtn = dark
    ? 'bg-white text-black hover:bg-gray-100'
    : 'bg-gray-900 text-white hover:bg-black';

  // ── Full-page loading spinner while fetching detail ──
  if (detailLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className={`animate-spin ${dark ? 'text-white/30' : 'text-gray-300'}`} size={24} />
      </div>
    );
  }

  // ── Detail view ──
  if (selected) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-10">
        <button
          onClick={() => setSelected(null)}
          className={`flex items-center gap-2 text-sm font-medium mb-6 px-3 py-2 rounded-xl border transition-all duration-200 ${backBtn}`}
        >
          <ArrowLeft size={14} />
          Back to recipes
        </button>
        <RecipeDetail recipe={selected} />
      </div>
    );
  }

  // ── List view ──
  return (
    <div className="max-w-5xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className={`p-2 rounded-xl ${dark ? 'bg-white/8' : 'bg-black/5'}`}>
              <BookOpen size={15} className={text} />
            </div>
            <span className={`text-xs font-medium tracking-widest uppercase ${muted}`}>My Recipes</span>
          </div>
          <h1 className={`text-3xl font-bold tracking-tight ${text}`}>Saved Recipes</h1>
          <p className={`text-sm mt-1 ${muted}`}>{total} recipe{total !== 1 ? 's' : ''} generated</p>
        </div>
        <button
          onClick={() => navigate('/recipes/generate')}
          className={`flex items-center gap-2 text-sm font-semibold px-4 py-2.5 rounded-xl transition-all duration-200 ${genBtn}`}
        >
          <Plus size={14} />
          Generate New
        </button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <Loader2 className={`animate-spin ${dark ? 'text-white/30' : 'text-gray-300'}`} size={24} />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className={`text-center py-12 text-sm ${dark ? 'text-red-400' : 'text-red-500'}`}>
          Failed to load recipes. Please try again.
        </div>
      )}

      {/* Empty state */}
      {!isLoading && recipes.length === 0 && (
        <div className="text-center py-20">
          <div className={`inline-flex p-4 rounded-2xl mb-4 ${dark ? 'bg-white/6' : 'bg-black/4'}`}>
            <ChefHat size={28} className={muted} />
          </div>
          <p className={`font-semibold mb-1 ${text}`}>No recipes yet</p>
          <p className={`text-sm mb-5 ${muted}`}>Generate your first AI-powered recipe</p>
          <button
            onClick={() => navigate('/recipes/generate')}
            className={`text-sm font-semibold px-5 py-2.5 rounded-xl transition-all duration-200 ${genBtn}`}
          >
            Generate Recipe
          </button>
        </div>
      )}

      {/* Grid */}
      {!isLoading && recipes.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {recipes.map((recipe) => (
              <RecipeCard
                key={recipe.recipe_id}
                recipe={recipe}
                onClick={() => handleCardClick(recipe)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-8">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className={`px-4 py-2 text-sm border rounded-xl transition-all duration-200 ${pageBtn}`}
              >
                ← Previous
              </button>
              <span className={`text-sm tabular-nums ${muted}`}>
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className={`px-4 py-2 text-sm border rounded-xl transition-all duration-200 ${pageBtn}`}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default RecipesPage;