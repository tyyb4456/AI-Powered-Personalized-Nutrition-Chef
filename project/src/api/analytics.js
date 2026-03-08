// src/api/analytics.js

import apiClient from './client';

export const generateProgressReport = async () => {
  const response = await apiClient.post('/analytics/progress', {});
  return response.data;
};

export const getProgressReport = async () => {
  const response = await apiClient.get('/analytics/progress');
  return response.data;
};

export const getLearnedPreferences = async () => {
  const response = await apiClient.get('/analytics/preferences');
  return response.data;
};

export const updateLearnedPreferences = async (data) => {
  const response = await apiClient.put('/analytics/preferences', data);
  return response.data;
};

export const resetLearnedPreferences = async () => {
  const response = await apiClient.delete('/analytics/preferences');
  return response.data;
};