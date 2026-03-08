/**
 * API 설정
 */

// 백엔드 API 기본 URL
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

// API 엔드포인트
export const API_ENDPOINTS = {
  health: `${API_BASE_URL}/api/health`,
  log: `${API_BASE_URL}/api/log`,
  ocr: `${API_BASE_URL}/api/ocr`,
  checkboxProcess: `${API_BASE_URL}/api/checkbox/process`,
};
