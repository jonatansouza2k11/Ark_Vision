import axios from 'axios'

// Base URL da API
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Axios instance
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Add token to requests if available
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Token inválido ou expirado
            localStorage.removeItem('token')
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

interface LoginRequest {
    username: string
    password: string
}

interface LoginResponse {
    access_token: string
    token_type: string
}

interface User {
    id: number
    username: string
    email: string
    role: string
}

export const authAPI = {
    /**
     * Faz login e retorna token JWT
     */
    login: async ({ username, password }: LoginRequest): Promise<LoginResponse> => {
        try {
            // 🐛 DEBUG: Log do que está sendo enviado
            console.log('🔐 Login attempt:', { username, password: '***' })
            console.log('🔐 API URL:', API_BASE_URL)
            console.log('🔐 Full URL:', `${API_BASE_URL}/api/v1/auth/login`)

            const payload = { username, password }
            console.log('🔐 Payload:', payload)

            const response = await api.post('/api/v1/auth/login', payload)

            console.log('✅ Login success:', response.data)

            // Salva token no localStorage
            if (response.data.access_token) {
                localStorage.setItem('token', response.data.access_token)
                console.log('✅ Token saved to localStorage')
            }

            return response.data
        } catch (error: any) {
            console.error('❌ Login error full:', error)
            console.error('❌ Error response:', error.response?.data)
            console.error('❌ Error status:', error.response?.status)
            console.error('❌ Error headers:', error.response?.headers)
            throw error
        }
    },

    /**
     * Retorna informações do usuário autenticado
     */
    me: async (): Promise<User> => {
        try {
            console.log('👤 Fetching current user...')
            const response = await api.get('/api/v1/auth/me')
            console.log('✅ User fetched:', response.data)
            return response.data
        } catch (error: any) {
            console.error('❌ Get user error:', error)
            console.error('❌ Error response:', error.response?.data)
            throw error
        }
    },

    /**
     * Faz logout (remove token do localStorage)
     */
    logout: async (): Promise<void> => {
        try {
            console.log('🚪 Logging out...')

            // Chama endpoint de logout (para logging no backend)
            try {
                await api.post('/api/v1/auth/logout')
            } catch (e) {
                // Ignora erro do backend, continua logout local
                console.warn('⚠️ Backend logout failed, continuing local logout')
            }

            // Remove token local
            localStorage.removeItem('token')
            console.log('✅ Logged out successfully')
        } catch (error) {
            console.error('❌ Logout error:', error)
            // Mesmo com erro, remove token local
            localStorage.removeItem('token')
        }
    },

    /**
     * Verifica se o usuário está autenticado
     */
    isAuthenticated: (): boolean => {
        const token = localStorage.getItem('token')
        return !!token
    },

    /**
     * Retorna o token atual
     */
    getToken: (): string | null => {
        return localStorage.getItem('token')
    },
}

export default api
