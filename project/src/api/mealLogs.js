// src/api/mealLogs.js

import apiClient from './client';

export const logMeal = async (payload) => {
  const response = await apiClient.post('/meal-logs/', payload);
  return response.data;
};

export const getMealLogs = async ({ dateFrom, dateTo, page = 1, limit = 20 } = {}) => {
  const params = { page, limit };
  if (dateFrom) params.date_from = dateFrom;
  if (dateTo)   params.date_to   = dateTo;
  const response = await apiClient.get('/meal-logs/', { params });
  return response.data;
};

export const getDailyAdherence = async (date) => {
  const response = await apiClient.get(`/meal-logs/adherence/${date}`);
  return response.data;
};

export const deleteMealLog = async (logId) => {
  const response = await apiClient.delete(`/meal-logs/${logId}`);
  return response.data;
};