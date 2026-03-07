// src/api/recipes.js

import apiClient from './client';

export const generateRecipe = async (payload = {}) => {
  const response = await apiClient.post('/recipes/generate', payload);
  return response.data;
};

export const listRecipes = async ({ page = 1, limit = 10 } = {}) => {
  const response = await apiClient.get('/recipes/', { params: { page, limit } });
  return response.data;
};

export const getRecipeById = async (recipeId) => {
  const response = await apiClient.get(`/recipes/${recipeId}`);
  return response.data;
};