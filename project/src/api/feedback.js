// src/api/feedback.js

import apiClient from './client';

export const submitFeedback = async ({ recipe_id, rating, comment }) => {
  const response = await apiClient.post('/feedback/', { recipe_id, rating, comment });
  return response.data;
};

/**
 * Check if the current user has already submitted feedback for a given recipe.
 * Returns the feedback object if found, throws if not (404 → catch in caller).
 */
export const getFeedbackForRecipe = async (recipeId) => {
  // The API returns a list — search for a matching recipe_id
  const response = await apiClient.get('/feedback/', { params: { limit: 100 } });
  const match = response.data.feedback?.find((f) => f.recipe_id === recipeId);
  if (!match) throw new Error('No feedback found');
  return match;
};

/**
 * Trigger the learning loop for a specific feedback entry.
 * Called immediately after submitFeedback so preferences update right away.
 */
export const triggerLearning = async (feedbackId) => {
  const response = await apiClient.post('/analytics/learn', { feedback_id: feedbackId });
  return response.data;
};