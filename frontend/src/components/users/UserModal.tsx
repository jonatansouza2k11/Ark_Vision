// frontend/src/components/users/UserModal.tsx
/**
 * ============================================================================
 * USER MODAL - v3.1 COMPLETE
 * ============================================================================
 * ✅ v2.0: Mantém toda funcionalidade original
 * ✅ v3.0: Validação avançada, password strength, melhor UX
 * ➕ v3.1: Adiciona campo is_active (somente edição)
 * ============================================================================
 */

import { useState, useEffect } from 'react';
import { X, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react';
import { User, UserCreate, UserUpdate } from '../../types/user';

// ============================================================================
// INTERFACE
// ============================================================================

interface UserModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (data: UserCreate | UserUpdate) => Promise<void>;
    user?: User;
    title: string;
}

// ============================================================================
// PASSWORD STRENGTH HELPER
// ============================================================================

interface PasswordStrength {
    score: number; // 0-4
    label: string;
    color: string;
    bgColor: string;
    suggestions: string[];
}

const calculatePasswordStrength = (password: string): PasswordStrength => {
    let score = 0;
    const suggestions: string[] = [];

    if (!password) {
        return {
            score: 0,
            label: 'Muito Fraca',
            color: 'text-gray-500',
            bgColor: 'bg-gray-200',
            suggestions: ['Digite uma senha'],
        };
    }

    // Length check
    if (password.length >= 8) score++;
    else suggestions.push('Use pelo menos 8 caracteres');

    if (password.length >= 12) score++;

    // Complexity checks
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    else suggestions.push('Use letras maiúsculas e minúsculas');

    if (/\d/.test(password)) score++;
    else suggestions.push('Inclua números');

    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
    else suggestions.push('Adicione caracteres especiais (!@#$%...)');

    // Determine label and color
    let label = 'Muito Fraca';
    let color = 'text-red-600';
    let bgColor = 'bg-red-500';

    if (score >= 4) {
        label = 'Muito Forte';
        color = 'text-green-600';
        bgColor = 'bg-green-500';
    } else if (score === 3) {
        label = 'Forte';
        color = 'text-blue-600';
        bgColor = 'bg-blue-500';
    } else if (score === 2) {
        label = 'Média';
        color = 'text-yellow-600';
        bgColor = 'bg-yellow-500';
    } else if (score === 1) {
        label = 'Fraca';
        color = 'text-orange-600';
        bgColor = 'bg-orange-500';
    }

    return { score, label, color, bgColor, suggestions };
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function UserModal({ isOpen, onClose, onSubmit, user, title }: UserModalProps) {
    // ============================================================================
    // STATE
    // ============================================================================

    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        role: 'user' as 'user' | 'admin',
        is_active: true, // ➕ v3.1: Campo is_active adicionado
    });

    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showPassword, setShowPassword] = useState(false);

    // ✅ v3.0: Validation states
    const [touched, setTouched] = useState({
        username: false,
        email: false,
        password: false,
    });

    const isEditing = !!user;

    // ✅ v3.0: Password strength
    const passwordStrength = calculatePasswordStrength(formData.password);

    // ============================================================================
    // VALIDATION
    // ============================================================================

    /**
     * ✅ v3.0: Validar email
     */
    const isValidEmail = (email: string): boolean => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    };

    /**
     * ✅ v3.0: Validar username
     */
    const isValidUsername = (username: string): boolean => {
        return username.length >= 3 && username.length <= 50 && /^[a-zA-Z0-9_-]+$/.test(username);
    };

    /**
     * ✅ v3.0: Validar formulário completo
     */
    const isFormValid = (): boolean => {
        if (isEditing) {
            // Ao editar, só valida campos que mudaram
            if (formData.email && !isValidEmail(formData.email)) return false;
            if (formData.password && formData.password.length < 6) return false;
            return true;
        } else {
            // Ao criar, valida tudo
            if (!isValidUsername(formData.username)) return false;
            if (!isValidEmail(formData.email)) return false;
            if (formData.password.length < 6) return false;
            return true;
        }
    };

    // ============================================================================
    // EFFECTS
    // ============================================================================

    /**
     * ✅ v3.1: Reset form quando modal abre/fecha (com is_active)
     */
    useEffect(() => {
        if (user) {
            setFormData({
                username: user.username,
                email: user.email,
                password: '',
                role: user.role,
                is_active: user.is_active ?? true, // ➕ v3.1: Lê is_active do usuário
            });
        } else {
            setFormData({
                username: '',
                email: '',
                password: '',
                role: 'user',
                is_active: true, // ➕ v3.1: Padrão é ativo ao criar
            });
        }

        setError('');
        setTouched({
            username: false,
            email: false,
            password: false,
        });
        setShowPassword(false);
    }, [user, isOpen]);

    // ============================================================================
    // HANDLERS
    // ============================================================================

    /**
     * ✅ v3.0: Handle blur (mark as touched)
     */
    const handleBlur = (field: keyof typeof touched) => {
        setTouched({ ...touched, [field]: true });
    };

    /**
     * ✅ v3.1: Handle submit (mantido + is_active)
     */
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // ✅ Previne múltiplos envios
        if (loading) {
            console.warn('⚠️ Formulário já está sendo processado');
            return;
        }

        // ✅ v3.0: Validação antes de enviar
        if (!isFormValid()) {
            setError('Por favor, corrija os erros antes de continuar');
            return;
        }

        setError('');
        setLoading(true);

        try {
            if (user) {
                // Editar: só envia campos modificados
                const updateData: UserUpdate = {};
                if (formData.email !== user.email) updateData.email = formData.email;
                if (formData.password) updateData.password = formData.password;
                if (formData.role !== user.role) updateData.role = formData.role;
                if (formData.is_active !== user.is_active) updateData.is_active = formData.is_active; // ➕ v3.1: Envia is_active se mudou

                if (Object.keys(updateData).length === 0) {
                    setError('Nenhuma alteração foi feita');
                    setLoading(false);
                    return;
                }

                await onSubmit(updateData);
            } else {
                // Criar: envia tudo (is_active sempre true por padrão)
                await onSubmit(formData as UserCreate);
            }

            // ✅ Delay visual antes de fechar
            setTimeout(() => {
                setLoading(false);
                onClose();
            }, 500);
        } catch (err: any) {
            const errorMessage = err?.response?.data?.detail || err?.message || 'Erro ao salvar usuário';
            setError(errorMessage);
            setLoading(false);
        }
    };

    // ============================================================================
    // RENDER
    // ============================================================================

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fadeIn">
            <div className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto animate-slideUp">
                {/* ========== HEADER ========== */}
                <div className="flex items-center justify-between p-6 border-b border-gray-200">
                    <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
                    <button
                        onClick={onClose}
                        disabled={loading}
                        className="text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* ========== FORM ========== */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {/* Error Alert */}
                    {error && (
                        <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm animate-shake">
                            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* Loading Alert */}
                    {loading && (
                        <div className="flex items-start gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-sm">
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 flex-shrink-0"></div>
                            <div>
                                <strong>⚙️ PROCESSANDO REQUISIÇÃO</strong>
                                <p className="text-xs mt-1">Aguarde... Não feche esta janela</p>
                            </div>
                        </div>
                    )}

                    {/* ========== USERNAME (criar) ========== */}
                    {!user && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Username <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                value={formData.username}
                                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                                onBlur={() => handleBlur('username')}
                                disabled={loading}
                                className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed ${touched.username && !isValidUsername(formData.username)
                                        ? 'border-red-300 focus:ring-red-500'
                                        : 'border-gray-300 focus:ring-blue-500'
                                    }`}
                                required
                                minLength={3}
                                maxLength={50}
                                placeholder="usuario123"
                                pattern="[a-zA-Z0-9_-]+"
                            />
                            {touched.username && !isValidUsername(formData.username) && (
                                <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                                    <AlertCircle className="w-3 h-3" />
                                    Username deve ter 3-50 caracteres (letras, números, _ ou -)
                                </p>
                            )}
                            {touched.username && isValidUsername(formData.username) && (
                                <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                                    <CheckCircle className="w-3 h-3" />
                                    Username válido
                                </p>
                            )}
                        </div>
                    )}

                    {/* ========== USERNAME (editar - readonly) ========== */}
                    {user && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                            <input
                                type="text"
                                value={formData.username}
                                disabled
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                            />
                            <p className="text-xs text-gray-500 mt-1">O username não pode ser alterado</p>
                        </div>
                    )}

                    {/* ========== EMAIL ========== */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Email <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="email"
                            value={formData.email}
                            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                            onBlur={() => handleBlur('email')}
                            disabled={loading}
                            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed ${touched.email && !isValidEmail(formData.email)
                                    ? 'border-red-300 focus:ring-red-500'
                                    : 'border-gray-300 focus:ring-blue-500'
                                }`}
                            required
                            placeholder="usuario@example.com"
                        />
                        {touched.email && !isValidEmail(formData.email) && (
                            <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                                <AlertCircle className="w-3 h-3" />
                                Digite um email válido
                            </p>
                        )}
                        {touched.email && isValidEmail(formData.email) && (
                            <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                                <CheckCircle className="w-3 h-3" />
                                Email válido
                            </p>
                        )}
                    </div>

                    {/* ========== PASSWORD ========== */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Senha {user && '(deixe vazio para não alterar)'}
                            {!user && <span className="text-red-500"> *</span>}
                        </label>
                        <div className="relative">
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={formData.password}
                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                onBlur={() => handleBlur('password')}
                                disabled={loading}
                                className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
                                required={!user}
                                minLength={6}
                                placeholder={user ? 'Deixe vazio para manter a atual' : '••••••'}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                            >
                                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                        </div>

                        {/* ✅ v3.0: Password strength indicator */}
                        {formData.password && (
                            <div className="mt-2 space-y-2">
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-gray-600">Força da senha:</span>
                                    <span className={`font-semibold ${passwordStrength.color}`}>{passwordStrength.label}</span>
                                </div>
                                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                    <div
                                        className={`h-full ${passwordStrength.bgColor} transition-all duration-300`}
                                        style={{ width: `${(passwordStrength.score / 4) * 100}%` }}
                                    ></div>
                                </div>
                                {passwordStrength.suggestions.length > 0 && (
                                    <ul className="text-xs text-gray-600 space-y-1 ml-4">
                                        {passwordStrength.suggestions.map((suggestion, index) => (
                                            <li key={index} className="list-disc">
                                                {suggestion}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        )}

                        {!user && !formData.password && (
                            <p className="text-xs text-gray-500 mt-1">Mínimo 6 caracteres</p>
                        )}
                    </div>

                    {/* ========== ROLE ========== */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Permissão <span className="text-red-500">*</span>
                        </label>
                        <select
                            value={formData.role}
                            onChange={(e) => setFormData({ ...formData, role: e.target.value as 'user' | 'admin' })}
                            disabled={loading}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed"
                            required
                        >
                            <option value="user">👤 User (Usuário Padrão)</option>
                            <option value="admin">🛡️ Admin (Administrador)</option>
                        </select>
                        <p className="text-xs text-gray-500 mt-1">
                            {formData.role === 'admin'
                                ? 'Administradores têm acesso total ao sistema'
                                : 'Usuários padrão têm acesso limitado'}
                        </p>
                    </div>

                    {/* ========== ➕ v3.1: IS_ACTIVE (SOMENTE EDIÇÃO) ========== */}
                    {user && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Status da Conta
                            </label>
                            <div className="flex items-center space-x-3 p-3 border border-gray-300 rounded-lg bg-gray-50">
                                <input
                                    type="checkbox"
                                    id="is_active"
                                    checked={formData.is_active}
                                    onChange={(e) =>
                                        setFormData({ ...formData, is_active: e.target.checked })
                                    }
                                    disabled={loading}
                                    className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-2 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                                />
                                <label
                                    htmlFor="is_active"
                                    className="flex-1 cursor-pointer select-none"
                                >
                                    <div className="font-medium text-gray-800">
                                        {formData.is_active ? '✅ Conta Ativa' : '❌ Conta Desativada'}
                                    </div>
                                    <div className="text-xs text-gray-600 mt-1">
                                        {formData.is_active
                                            ? 'Usuário pode fazer login normalmente'
                                            : '⚠️ Usuário NÃO poderá fazer login'}
                                    </div>
                                </label>
                            </div>
                        </div>
                    )}

                    {/* ========== ACTIONS ========== */}
                    <div className="flex gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={loading}
                            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Cancelar
                        </button>

                        <button
                            type="submit"
                            disabled={loading || !isFormValid()}
                            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                        >
                            {loading ? (
                                <span className="flex items-center justify-center gap-2">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    PROCESSANDO...
                                </span>
                            ) : (
                                <>{isEditing ? 'Atualizar' : 'Criar'}</>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
