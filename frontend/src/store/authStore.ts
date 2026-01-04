// src/store/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '../types/user';

interface AuthState {
    user: User | null;
    token: string | null;
    login: (user: User, token: string) => void;
    logout: () => void;
    isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set, get) => ({
            user: null,
            token: null,

            login: (user, token) => {
                set({ user, token });
                // ✅ Salvar no localStorage para compatibilidade com interceptor da API
                localStorage.setItem('access_token', token);
                localStorage.setItem('user', JSON.stringify(user));
                console.log('✅ [Store] User and token saved');
            },

            logout: () => {
                set({ user: null, token: null });
                // ✅ Limpar tudo do localStorage
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                localStorage.removeItem('token');
                console.log('✅ [Store] User logged out');
            },

            isAuthenticated: () => {
                return !!get().token;
            },
        }),
        {
            name: 'auth-storage',
        }
    )
);
