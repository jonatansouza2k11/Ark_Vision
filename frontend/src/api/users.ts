// src/api/users.ts
import { User, UserCreate, UserUpdate } from '../types/user';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper para obter token
const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
    };
};

export const usersApi = {
    // Listar todos usuários (admin only)
    async getAll(skip = 0, limit = 100): Promise<User[]> {
        const response = await fetch(
            `${API_URL}/api/v1/users/?skip=${skip}&limit=${limit}`,
            {
                headers: getAuthHeaders(),
            }
        );

        if (!response.ok) {
            throw new Error('Erro ao buscar usuários');
        }

        return response.json();
    },

    // Obter usuário atual
    async getMe(): Promise<User> {
        const response = await fetch(`${API_URL}/api/v1/users/me`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error('Erro ao buscar usuário atual');
        }

        return response.json();
    },

    // Obter usuário por ID
    async getById(id: number): Promise<User> {
        const response = await fetch(`${API_URL}/api/v1/users/${id}`, {
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            throw new Error(`Erro ao buscar usuário ${id}`);
        }

        return response.json();
    },

    // Criar usuário (via registro)
    async create(data: UserCreate): Promise<User> {
        const response = await fetch(`${API_URL}/api/v1/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao criar usuário');
        }

        return response.json();
    },

    // Atualizar usuário
    async update(id: number, data: UserUpdate): Promise<User> {
        const response = await fetch(`${API_URL}/api/v1/users/${id}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao atualizar usuário');
        }

        return response.json();
    },

    // Deletar usuário (admin only)
    async delete(id: number): Promise<void> {
        const response = await fetch(`${API_URL}/api/v1/users/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao deletar usuário');
        }
    },
};
