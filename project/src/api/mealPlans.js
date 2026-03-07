// src/api/mealPlans.js

import apiClient from './client';

export const generateMealPlan = async () => {
  const response = await apiClient.post('/meal-plans/generate', {});
  return response.data;
};

export const getActivePlan = async () => {
  const response = await apiClient.get('/meal-plans/active');
  return response.data;
};

export const listMealPlans = async () => {
  const response = await apiClient.get('/meal-plans/');
  return response.data;
};

export const getMealPlanById = async (planId) => {
  const response = await apiClient.get(`/meal-plans/${planId}`);
  return response.data;
};

export const getGroceryList = async (planId) => {
  const response = await apiClient.get(`/meal-plans/${planId}/grocery`);
  return response.data;
};

export const getPrepSchedule = async (planId) => {
  const response = await apiClient.get(`/meal-plans/${planId}/prep`);
  return response.data;
};