// src/store/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '../types/user';

interface AuthState {
    user: User | null;
    token: string | null;
    login: (user: User, token: string) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            login: (user, token) => {
                set({ user, token });
                // Também salvar no localStorage para compatibilidade
                localStorage.setItem('token', token);
            },
            logout: () => {
                set({ user: null, token: null });
                localStorage.removeItem('token');
            },
        }),
        {
            name: 'auth-storage', // Nome da chave no localStorage
        }
    )
);
