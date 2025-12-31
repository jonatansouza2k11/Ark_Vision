export interface User {
    id: number;
    username: string;
    email: string;
    role: 'admin' | 'user';
    created_at: string;
    last_login: string | null;
}

export interface LoginRequest {
    username: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface RegisterRequest {
    username: string;
    email: string;
    password: string;
    role?: 'admin' | 'user';
}
