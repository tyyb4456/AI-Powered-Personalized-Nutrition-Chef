// src/api/feedback.js

import apiClient from './client';

export const submitFeedback = async ({ recipe_id, rating, comment }) => {
  const response = await apiClient.post('/feedback/', { recipe_id, rating, comment });
  return response.data;
};

export const getFeedbackForRecipe = async (recipe_id) => {
  const response = await apiClient.get('/feedback/', { params: { recipe_id, limit: 1 } });
  return response.data?.feedback?.[0] || null;
};

// Add to imports in feedback.js
export const triggerLearning = async (feedback_id) => {
  const response = await apiClient.post('/analytics/learn', { feedback_id });
  return response.data;
};