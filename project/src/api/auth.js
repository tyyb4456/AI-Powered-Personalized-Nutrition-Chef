// src/api/auth.js

import apiClient from './client';

export const registerUser = async ({ name, email, password }) => {
  const response = await apiClient.post('/auth/register', { name, email, password });
  return response.data;
};

export const loginUser = async ({ name, password }) => {
  const response = await apiClient.post('/auth/login', { name, password });
  return response.data;
};