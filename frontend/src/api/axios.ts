import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { ApiError } from '../types/api.types';

// ✅ CORRIGIDO: Sem /api/v1 no fallback
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api: AxiosInstance = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 10000,
});

api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = localStorage.getItem('token');
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.href = '/login';
        }

        const apiError: ApiError = {
            detail: error.response?.data?.detail || 'Erro desconhecido',
        };

        return Promise.reject(apiError);
    }
);

export default api;
