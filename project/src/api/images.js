// src/api/images.js

import apiClient from './client';

export const analyseImageBase64 = async ({ image_base64, mime_type = 'image/jpeg', auto_log = false, meal_slot, log_date }) => {
  const payload = { image_base64, mime_type, auto_log };
  if (meal_slot) payload.meal_slot = meal_slot;
  if (log_date)  payload.log_date  = log_date;
  const response = await apiClient.post('/images/analyse', payload);
  return response.data;
};