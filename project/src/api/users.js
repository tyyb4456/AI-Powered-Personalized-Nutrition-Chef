// src/api/users.js

import apiClient from './client';

export const getMyProfile = async () => {
  const response = await apiClient.get('/users/me');
  return response.data;
};

export const updateMyProfile = async (data) => {
  const response = await apiClient.put('/users/me', data);
  return response.data;
};