// src/types/user.ts
export type UserRole = 'user' | 'admin';

export interface User {
    id: number;
    username: string;
    email: string;
    role: UserRole;
    created_at: string;
    last_login: string | null;
}

export interface UserCreate {
    username: string;
    email: string;
    password: string;
    role: UserRole;
}

export interface UserUpdate {
    email?: string;
    password?: string;
    role?: UserRole;
}

export interface UsersResponse {
    users: User[];
    total: number;
}
