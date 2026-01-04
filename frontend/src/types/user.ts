// frontend/src/types/user.ts
/**
 * ============================================================================
 * USER TYPES - v3.1 COMPLETE
 * ============================================================================
 * ✅ v2.0: Mantido 100% compatível
 * ✅ v3.0: Novos tipos para recursos avançados
 * ➕ v3.1: Campo is_active adicionado
 */

// ============================================================================
// v3.1 TYPES - BASE (ATUALIZADOS) ✅
// ============================================================================

/**
 * ✅ v3.1: User base (com is_active)
 */
export interface User {
    id: number;
    username: string;
    email: string;
    role: 'user' | 'admin';
    is_active: boolean; // ➕ v3.1: Campo is_active
    created_at: string;
    last_login: string | null;
}

/**
 * ✅ v2.0: Criar usuário (registro)
 */
export interface UserCreate {
    username: string;
    email: string;
    password: string;
    role?: 'user' | 'admin';
    // is_active não é necessário no create (padrão: true no backend)
}

/**
 * ✅ v3.1: Atualizar usuário (com is_active)
 */
export interface UserUpdate {
    email?: string;
    password?: string;
    role?: 'user' | 'admin';
    is_active?: boolean; // ➕ v3.1: Campo is_active
}

// ============================================================================
// v3.0 NEW TYPES - EXTENDED ➕
// ============================================================================

/**
 * ➕ NEW v3.0: User estendido (com campos extras)
 */
export interface UserExtended extends User {
    full_name?: string | null;
    phone?: string | null;
    department?: string | null;
    position?: string | null;
    account_status: AccountStatus;
    email_verified: boolean;
    two_factor_enabled: boolean;
    updated_at: string;
    last_password_change: string | null;
}

/**
 * ➕ NEW v3.0: Status da conta
 */
export enum AccountStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
    SUSPENDED = 'suspended',
    PENDING = 'pending',
}

/**
 * ➕ NEW v3.0: Parâmetros de busca avançada
 */
export interface UserSearchParams {
    search_term?: string;
    role?: 'user' | 'admin';
    status?: AccountStatus;
    email_verified?: boolean;
    two_factor_enabled?: boolean;
    created_after?: string;
    created_before?: string;
    last_login_after?: string;
    last_login_before?: string;
    sort_by?: SortField;
    sort_order?: SortOrder;
    limit?: number;
    offset?: number;
}

/**
 * ➕ NEW v3.0: Campos de ordenação
 */
export type SortField =
    | 'id'
    | 'username'
    | 'email'
    | 'role'
    | 'created_at'
    | 'last_login'
    | 'updated_at';

/**
 * ➕ NEW v3.0: Ordem de ordenação
 */
export type SortOrder = 'asc' | 'desc';

/**
 * ➕ NEW v3.0: Resposta de busca paginada
 */
export interface UserSearchResponse {
    users: User[];
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
}

// ============================================================================
// v3.0 BULK OPERATIONS ➕
// ============================================================================

/**
 * ➕ NEW v3.0: Criar múltiplos usuários
 */
export interface UserBulkCreateRequest {
    users: UserCreate[];
    send_welcome_email?: boolean;
}

/**
 * ➕ NEW v3.0: Resposta de criação em lote
 */
export interface UserBulkCreateResponse {
    created: User[];
    failed: Array<{
        user_data: UserCreate;
        error: string;
    }>;
    summary: {
        total_attempted: number;
        successful: number;
        failed: number;
    };
}

/**
 * ➕ NEW v3.0: Deletar múltiplos usuários
 */
export interface UserBulkDeleteRequest {
    user_ids: number[];
}

/**
 * ➕ NEW v3.0: Resposta de deleção em lote
 */
export interface UserBulkDeleteResponse {
    deleted: number;
    failed: number;
    errors: Array<{
        user_id: number;
        error: string;
    }>;
    successful: boolean;
}

// ============================================================================
// v3.0 USER MANAGEMENT ➕
// ============================================================================

/**
 * ➕ NEW v3.0: Reset de senha
 */
export interface PasswordResetRequest {
    new_password: string;
    notify_user?: boolean;
}

/**
 * ➕ NEW v3.0: Resposta de reset de senha
 */
export interface PasswordResetResponse {
    message: string;
    user_id: number;
    username: string;
    password_changed_at: string;
}

/**
 * ➕ NEW v3.0: Atualizar status da conta
 */
export interface UserStatusUpdate {
    status: AccountStatus;
    reason?: string;
    notify_user?: boolean;
}

/**
 * ➕ NEW v3.0: Resposta de atualização de status
 */
export interface UserStatusUpdateResponse {
    message: string;
    user_id: number;
    username: string;
    old_status: AccountStatus;
    new_status: AccountStatus;
    updated_at: string;
}

// ============================================================================
// v3.0 ACTIVITY & STATISTICS ➕
// ============================================================================

/**
 * ➕ NEW v3.0: Atividade do usuário
 */
export interface UserActivity {
    timestamp: string;
    action: string;
    details: string | null;
    ip_address: string | null;
}

/**
 * ➕ NEW v3.0: Resposta de atividade
 */
export interface UserActivityResponse {
    user_id: number;
    username: string;
    activities: UserActivity[];
    total_activities: number;
}

/**
 * ➕ NEW v3.0: Estatísticas gerais
 */
export interface UserStatistics {
    total_users: number;
    active_users: number;
    inactive_users: number;
    admin_users: number;
    regular_users: number;
    users_created_last_30_days: number;
    users_logged_in_last_24h: number;
    email_verified_users: number;
    two_factor_enabled_users: number;
}

// ============================================================================
// v3.0 EXPORT / IMPORT ➕
// ============================================================================

/**
 * ➕ NEW v3.0: Formato de exportação
 */
export enum ExportFormat {
    JSON = 'json',
    CSV = 'csv',
}

/**
 * ➕ NEW v3.0: Opções de exportação
 */
export interface ExportOptions {
    format: ExportFormat;
    include_inactive?: boolean;
    fields?: string[];
}
