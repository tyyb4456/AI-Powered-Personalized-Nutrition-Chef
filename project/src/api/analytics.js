// src/api/analytics.js

import apiClient from './client';

export const generateProgressReport = async () => {
  const response = await apiClient.post('/analytics/progress', {});
  return response.data;
};

export const getProgressReport = async () => {
  try {
    const response = await apiClient.get('/analytics/progress');
    return response.data;
  } catch (err) {
    // 404 means no report yet — return null instead of throwing
    if (err.response?.status === 404) return null;
    throw err;
  }
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