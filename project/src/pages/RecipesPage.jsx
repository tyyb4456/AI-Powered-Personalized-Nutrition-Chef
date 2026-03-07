// src/pages/RecipesPage.jsx

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BookOpen, Loader2, ChefHat, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { listRecipes } from '../api/recipes';
import RecipeCard from '../components/recipe/RecipeCard';
import RecipeDetail from '../components/recipe/RecipeDetail';

const RecipesPage = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ['recipes', page],
    queryFn: () => listRecipes({ page, limit: 12 }),
  });

  const recipes = data?.recipes || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 12);

  if (selected) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <button
          onClick={() => setSelected(null)}
          className="text-sm text-primary-600 hover:underline mb-4 flex items-center gap-1"
        >
          ← Back to recipes
        </button>
        <RecipeDetail recipe={selected} />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-50 rounded-lg">
            <BookOpen className="text-primary-600" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Recipes</h1>
            <p className="text-sm text-gray-500">{total} recipes generated</p>
          </div>
        </div>
        <button
          onClick={() => navigate('/recipes/generate')}
          className="flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors"
        >
          <Plus size={16} />
          Generate New
        </button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="animate-spin text-primary-600" size={28} />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-12 text-red-500 text-sm">
          Failed to load recipes. Please try again.
        </div>
      )}

      {/* Empty state */}
      {!isLoading && recipes.length === 0 && (
        <div className="text-center py-16">
          <ChefHat size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500 font-medium">No recipes yet</p>
          <p className="text-sm text-gray-400 mt-1 mb-4">Generate your first AI-powered recipe</p>
          <button
            onClick={() => navigate('/recipes/generate')}
            className="bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition-colors"
          >
            Generate Recipe
          </button>
        </div>
      )}

      {/* Grid */}
      {!isLoading && recipes.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recipes.map((recipe) => (
              <RecipeCard
                key={recipe.recipe_id}
                recipe={recipe}
                onClick={() => setSelected(recipe)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default RecipesPage;