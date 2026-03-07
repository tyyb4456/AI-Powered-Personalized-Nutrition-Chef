// src/api/feedback.js

import apiClient from './client';

export const submitFeedback = async ({ recipe_id, rating, comment }) => {
  const response = await apiClient.post('/feedback/', { recipe_id, rating, comment });
  return response.data;
};