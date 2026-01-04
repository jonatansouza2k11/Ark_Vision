// frontend/src/api/users.ts
/**
 * ============================================================================
 * USERS API CLIENT - v2.0 + v3.0 COMPLETE
 * ============================================================================
 * ✅ v2.0: Mantido 100% compatível (seus métodos originais)
 * ➕ v3.0: 10 novos endpoints adicionados
 * 
 * Total: 15 endpoints (5 v2.0 + 10 v3.0)
 */


import type {
    User,
    UserCreate,
    UserUpdate,
    UserSearchParams,
    UserSearchResponse,
    UserBulkCreateRequest,
    UserBulkCreateResponse,
    UserBulkDeleteRequest,
    UserBulkDeleteResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    UserStatusUpdate,
    UserStatusUpdateResponse,
    UserActivityResponse,
    UserStatistics,
    UserExtended
} from '../types/user';


// ✅ CORREÇÃO: Import ExportFormat como valor (não type)
import { ExportFormat } from '../types/user';


const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';


// ============================================================================
// HELPER FUNCTIONS
// ============================================================================


/**
 * ✅ Helper para obter token (mantido do v2.0)
 */
const getAuthHeaders = () => {
    const token = localStorage.getItem('access_token');
    return {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
    };
};


/**
 * ➕ NEW: Handle API errors
 */
const handleApiError = async (response: Response): Promise<never> => {
    let errorMessage = 'Erro na requisição';
    try {
        const error = await response.json();
        errorMessage = error.detail || error.message || errorMessage;
    } catch {
        errorMessage = `Erro ${response.status}: ${response.statusText}`;
    }
    throw new Error(errorMessage);
};


// ============================================================================
// v2.0 ENDPOINTS - MANTIDOS (SEU CÓDIGO ORIGINAL) ✅
// ============================================================================


/**
 * ✅ v2.0: Listar todos usuários (admin only)
 * 🔧 FIXED: Removida barra final da URL
 */
const getAll = async (): Promise<User[]> => {
    const response = await fetch(
        `${API_URL}/api/v1/users`,  // ← 🔧 REMOVIDA BARRA FINAL
        {
            headers: getAuthHeaders(),
        }
    );


    if (!response.ok) {
        throw new Error('Erro ao buscar usuários');
    }


    return response.json();
};


/**
 * ✅ v2.0: Obter usuário atual
 */
const getMe = async (): Promise<User> => {
    const response = await fetch(`${API_URL}/api/v1/users/me`, {
        headers: getAuthHeaders(),
    });


    if (!response.ok) {
        throw new Error('Erro ao buscar usuário atual');
    }


    return response.json();
};


/**
 * ✅ v2.0: Obter usuário por ID
 */
const getById = async (id: number): Promise<User> => {
    const response = await fetch(`${API_URL}/api/v1/users/${id}`, {
        headers: getAuthHeaders(),
    });


    if (!response.ok) {
        throw new Error(`Erro ao buscar usuário ${id}`);
    }


    return response.json();
};


/**
 * ✅ v2.0: Criar usuário (via registro)
 */
const create = async (data: UserCreate): Promise<User> => {
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
};


/**
 * ✅ v2.0: Atualizar usuário
 */
const update = async (id: number, data: UserUpdate): Promise<User> => {
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
};


/**
 * ✅ v2.0: Deletar usuário (admin only)
 */
const deleteUser = async (id: number): Promise<void> => {
    const response = await fetch(`${API_URL}/api/v1/users/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });


    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Erro ao deletar usuário');
    }
};


// ============================================================================
// v3.0 NEW ENDPOINTS - SEARCH & FILTER ➕
// ============================================================================


/**
 * ➕ NEW v3.0: Busca avançada de usuários
 * Endpoint: POST /api/v1/users/search
 */
const searchUsers = async (params: UserSearchParams): Promise<UserSearchResponse> => {
    const response = await fetch(`${API_URL}/api/v1/users/search`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(params),
    });


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


// ============================================================================
// v3.0 NEW ENDPOINTS - BULK OPERATIONS ➕
// ============================================================================


/**
 * ➕ NEW v3.0: Cria múltiplos usuários em lote
 * Endpoint: POST /api/v1/users/bulk/create
 */
const bulkCreate = async (
    users: UserCreate[],
    sendWelcomeEmail = false
): Promise<UserBulkCreateResponse> => {
    const requestData: UserBulkCreateRequest = {
        users,
        send_welcome_email: sendWelcomeEmail,
    };


    const response = await fetch(`${API_URL}/api/v1/users/bulk/create`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(requestData),
    });


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


/**
 * ➕ NEW v3.0: Deleta múltiplos usuários em lote
 * Endpoint: POST /api/v1/users/bulk/delete
 */
const bulkDelete = async (userIds: number[]): Promise<UserBulkDeleteResponse> => {
    const requestData: UserBulkDeleteRequest = {
        user_ids: userIds,
    };


    const response = await fetch(`${API_URL}/api/v1/users/bulk/delete`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(requestData),
    });


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


// ============================================================================
// v3.0 NEW ENDPOINTS - USER MANAGEMENT ➕
// ============================================================================


/**
 * ➕ NEW v3.0: Atualiza usuário completo (mais campos que v2.0)
 * Endpoint: PUT /api/v1/users/{user_id}
 * Nota: Usa mesma rota que v2.0 update, mas aceita mais campos
 */
const updateComplete = async (
    id: number,
    data: Partial<UserExtended>
): Promise<UserExtended> => {
    const response = await fetch(`${API_URL}/api/v1/users/${id}`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify(data),
    });


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


/**
 * ➕ NEW v3.0: Reset senha do usuário
 * Endpoint: POST /api/v1/users/{user_id}/reset-password
 */
const resetPassword = async (
    userId: number,
    passwordData: PasswordResetRequest
): Promise<PasswordResetResponse> => {
    const response = await fetch(
        `${API_URL}/api/v1/users/${userId}/reset-password`,
        {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(passwordData),
        }
    );


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


/**
 * ➕ NEW v3.0: Atualiza status da conta (ativa/desativa/suspende)
 * Endpoint: PATCH /api/v1/users/{user_id}/status
 */
const updateStatus = async (
    userId: number,
    statusData: UserStatusUpdate
): Promise<UserStatusUpdateResponse> => {
    const response = await fetch(
        `${API_URL}/api/v1/users/${userId}/status`,
        {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify(statusData),
        }
    );


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


/**
 * ➕ NEW v3.0: Atualiza role do usuário (compatível com v2.0)
 * Endpoint: PATCH /api/v1/users/{user_id}/role
 */
const updateRole = async (
    userId: number,
    role: 'user' | 'admin'
): Promise<{ message: string; user_id: number; username: string; new_role: string }> => {
    const response = await fetch(
        `${API_URL}/api/v1/users/${userId}/role?role=${role}`,
        {
            method: 'PATCH',
            headers: getAuthHeaders(),
        }
    );


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


// ============================================================================
// v3.0 NEW ENDPOINTS - ACTIVITY & STATISTICS ➕
// ============================================================================


/**
 * ➕ NEW v3.0: Obtém atividade/histórico do usuário
 * Endpoint: GET /api/v1/users/{user_id}/activity
 */
const getActivity = async (userId: number): Promise<UserActivityResponse> => {
    const response = await fetch(
        `${API_URL}/api/v1/users/${userId}/activity`,
        {
            headers: getAuthHeaders(),
        }
    );


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


/**
 * ➕ NEW v3.0: Obtém estatísticas gerais de usuários
 * Endpoint: GET /api/v1/users/statistics
 */
const getStatistics = async (): Promise<UserStatistics> => {
    const response = await fetch(`${API_URL}/api/v1/users/statistics`, {
        headers: getAuthHeaders(),
    });


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


// ============================================================================
// v3.0 NEW ENDPOINTS - EXPORT / IMPORT ➕
// ============================================================================

/**
 * ➕ NEW v3.0: Exporta usuários (JSON ou CSV) No moemento somente CSV no frontend
 * Endpoint: GET /api/v1/users/export
 */
const exportUsers = async (format: ExportFormat = ExportFormat.JSON): Promise<Blob> => {
    // ✅ Extrai o valor string do enum de forma explícita
    const formatParam = format === ExportFormat.JSON ? 'json' : 'csv';

    console.log(`📤 Exporting users as ${formatParam.toUpperCase()}...`);

    const response = await fetch(
        `${API_URL}/api/v1/users/export?format=${formatParam}`,
        {
            headers: getAuthHeaders(),
        }
    );

    if (!response.ok) {
        console.error(`❌ Export failed with status ${response.status}`);
        await handleApiError(response);
    }

    console.log(`✅ Export successful! Content-Type: ${response.headers.get('content-type')}`);
    return response.blob();
};


/**
 * ➕ NEW v3.0: Importa usuários de arquivo
 * Endpoint: POST /api/v1/users/import
 */
const importUsers = async (file: File): Promise<UserBulkCreateResponse> => {
    const formData = new FormData();
    formData.append('file', file);


    const token = localStorage.getItem('access_token');
    const headers: HeadersInit = {};
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }


    const response = await fetch(`${API_URL}/api/v1/users/import`, {
        method: 'POST',
        headers,
        body: formData,
    });


    if (!response.ok) {
        await handleApiError(response);
    }


    return response.json();
};


// ============================================================================
// UTILITY FUNCTIONS ➕
// ============================================================================


/**
 * ➕ NEW: Download arquivo exportado
 */
const downloadExport = (blob: Blob, format: ExportFormat) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `users_export_${new Date().toISOString().split('T')[0]}.${format}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
};


/**
 * ➕ NEW: Exporta e faz download automaticamente
 */
const exportAndDownload = async (format: ExportFormat = ExportFormat.JSON): Promise<void> => {
    try {
        const blob = await exportUsers(format);
        downloadExport(blob, format);
    } catch (error) {
        console.error('Erro ao exportar usuários:', error);
        throw error;
    }
};


// ============================================================================
// EXPORT API OBJECT
// ============================================================================


export const usersApi = {
    // ========== v2.0 METHODS (MANTIDOS) ✅ ==========
    getAll,
    getMe,
    getById,
    create,
    update,
    delete: deleteUser,


    // ========== v3.0 NEW METHODS ➕ ==========
    // Search & Filter
    searchUsers,


    // Bulk Operations
    bulkCreate,
    bulkDelete,


    // User Management
    updateComplete,
    resetPassword,
    updateStatus,
    updateRole,


    // Activity & Statistics
    getActivity,
    getStatistics,


    // Export / Import
    exportUsers,
    importUsers,


    // Utilities
    downloadExport,
    exportAndDownload,
};


// Default export (compatibilidade)
export default usersApi;
