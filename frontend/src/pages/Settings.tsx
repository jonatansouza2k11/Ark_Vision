// frontend/src/pages/Settings.tsx

import { useState, useEffect } from 'react';
import {
    Settings as SettingsIcon,
    Save,
    RotateCcw,
    Camera,
    Mail,
    Cpu,
    Shield,
    AlertCircle,
    CheckCircle2,
    RefreshCw
} from 'lucide-react';
import MainLayout from '../components/layout/MainLayout';
import { SettingsInput } from '../components/Settings/SettingsInput';
import { useSettings } from '../hooks/useSettings';
import { settingsApi, type YOLOModel } from '../api/settingsApi';
import type { SettingsTab, AllSettings } from '../types/settings.types';

export default function Settings() {
    const {
        settings,
        loading,
        saving,
        error,
        updateYoloConfig,
        updateEmailConfig,
        updateSettings,
        resetSettings,
    } = useSettings();

    const [activeTab, setActiveTab] = useState<SettingsTab>('yolo');
    const [formData, setFormData] = useState<Partial<AllSettings>>({});
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    // ✅ Estados para modelos YOLO - SEMPRE inicializa como array
    const [yoloModels, setYoloModels] = useState<YOLOModel[]>([]);
    const [currentModel, setCurrentModel] = useState<string>('');
    const [loadingModels, setLoadingModels] = useState(false);

    // Sync form data with loaded settings
    useEffect(() => {
        if (settings) {
            setFormData({ ...settings });
        }
    }, [settings]);

    // ✅ Carregar modelos YOLO ao montar o componente
    useEffect(() => {
        loadYoloModels();
    }, []);

    // ✅ Função para carregar modelos disponíveis com tratamento robusto
    const loadYoloModels = async () => {
        try {
            setLoadingModels(true);
            const response = await settingsApi.getYoloModels();

            // ✅ Validação robusta da resposta
            if (response && typeof response === 'object') {
                const models = Array.isArray(response.models) ? response.models : [];
                setYoloModels(models);
                setCurrentModel(response.current || '');
                console.log('✅ Modelos YOLO carregados:', models.length, 'modelo(s)');
            } else {
                console.warn('⚠️ Resposta inválida da API:', response);
                setYoloModels([]);
                setCurrentModel('');
            }
        } catch (err) {
            console.error('❌ Erro ao carregar modelos YOLO:', err);
            setYoloModels([]);
            setCurrentModel('');
        } finally {
            setLoadingModels(false);
        }
    };

    const tabs = [
        { id: 'yolo' as const, label: 'YOLO Model', icon: Camera },
        { id: 'zones' as const, label: 'Zonas', icon: Shield },
        { id: 'email' as const, label: 'Email/SMTP', icon: Mail },
        { id: 'system' as const, label: 'Sistema', icon: Cpu },
    ];

    const handleInputChange = (name: string, value: any) => {
        setFormData((prev) => ({ ...prev, [name]: value }));
    };

    const handleSave = async () => {
        setSuccessMessage(null);
        let success = false;

        try {
            if (activeTab === 'yolo') {
                success = await updateYoloConfig({
                    model_path: formData.model_path,
                    conf_thresh: formData.conf_thresh,
                    target_width: formData.target_width,
                    frame_step: formData.frame_step,
                    tracker: formData.tracker,
                    source: formData.source,
                    cam_width: formData.cam_width,
                    cam_height: formData.cam_height,
                    cam_fps: formData.cam_fps,
                });
            } else if (activeTab === 'zones') {
                success = await updateSettings({
                    max_out_time: formData.max_out_time,
                    email_cooldown: formData.email_cooldown,
                    zone_empty_timeout: formData.zone_empty_timeout,
                    zone_full_timeout: formData.zone_full_timeout,
                    zone_full_threshold: formData.zone_full_threshold,
                    buffer_seconds: formData.buffer_seconds,
                });
            } else if (activeTab === 'email') {
                success = await updateEmailConfig({
                    email_smtp_server: formData.email_smtp_server,
                    email_smtp_port: formData.email_smtp_port,
                    email_user: formData.email_user,
                    email_password: formData.email_password,
                    email_from: formData.email_from,
                });
            } else if (activeTab === 'system') {
                success = await updateSettings({
                    use_cuda: formData.use_cuda,
                    verbose_logs: formData.verbose_logs,
                    auto_restart: formData.auto_restart,
                });
            }

            if (success) {
                setSuccessMessage('✅ Configurações salvas com sucesso!');
                setTimeout(() => setSuccessMessage(null), 3000);
            }
        } catch (err) {
            console.error('Failed to save settings:', err);
        }
    };

    const handleReset = async () => {
        if (window.confirm('⚠️ Deseja restaurar todas as configurações para os valores padrão?')) {
            const success = await resetSettings();
            if (success) {
                setSuccessMessage('✅ Configurações restauradas com sucesso!');
                setTimeout(() => setSuccessMessage(null), 3000);
            }
        }
    };

    if (loading) {
        return (
            <MainLayout>
                <div className="flex items-center justify-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
            </MainLayout>
        );
    }

    return (
        <MainLayout>
            <div className="space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                            <SettingsIcon className="w-8 h-8" />
                            Configurações
                        </h1>
                        <p className="text-gray-600 mt-1">Gerencie as configurações do sistema</p>
                    </div>

                    <div className="flex gap-3">
                        <button
                            onClick={handleReset}
                            disabled={saving}
                            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <RotateCcw className="w-4 h-4" />
                            Restaurar Padrões
                        </button>
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <Save className="w-4 h-4" />
                            {saving ? 'Salvando...' : 'Salvar Alterações'}
                        </button>
                    </div>
                </div>

                {/* Messages */}
                {error && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3 animate-in fade-in duration-300">
                        <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                        <div>
                            <h3 className="font-medium text-red-900">Erro</h3>
                            <p className="text-sm text-red-700">{error}</p>
                        </div>
                    </div>
                )}

                {successMessage && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3 animate-in fade-in duration-300">
                        <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-green-700">{successMessage}</p>
                    </div>
                )}

                {/* Tabs */}
                <div className="bg-white rounded-lg shadow">
                    <div className="border-b border-gray-200">
                        <div className="flex space-x-8 px-6">
                            {tabs.map((tab) => {
                                const Icon = tab.icon;
                                return (
                                    <button
                                        key={tab.id}
                                        onClick={() => setActiveTab(tab.id)}
                                        className={`flex items-center gap-2 py-4 px-2 border-b-2 font-medium text-sm transition-colors ${activeTab === tab.id
                                                ? 'border-blue-600 text-blue-600'
                                                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                            }`}
                                    >
                                        <Icon className="w-5 h-5" />
                                        {tab.label}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    <div className="p-6">
                        {/* YOLO Tab */}
                        {activeTab === 'yolo' && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* ✅ Campo de Modelo YOLO - Select dinâmico com verificações robustas */}
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <label htmlFor="model_path" className="block text-sm font-medium text-gray-700">
                                            Modelo YOLO
                                        </label>
                                        <button
                                            onClick={loadYoloModels}
                                            disabled={loadingModels}
                                            className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 disabled:opacity-50"
                                            title="Recarregar lista de modelos"
                                        >
                                            <RefreshCw className={`w-3 h-3 ${loadingModels ? 'animate-spin' : ''}`} />
                                            Atualizar
                                        </button>
                                    </div>

                                    <select
                                        id="model_path"
                                        name="model_path"
                                        value={formData.model_path || ''}
                                        onChange={(e) => handleInputChange('model_path', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        disabled={loadingModels}
                                    >
                                        {loadingModels ? (
                                            <option>Carregando modelos...</option>
                                        ) : !Array.isArray(yoloModels) || yoloModels.length === 0 ? (
                                            <option>Nenhum modelo encontrado</option>
                                        ) : (
                                            <>
                                                <option value="">Selecione um modelo</option>
                                                {yoloModels.map((model) => (
                                                    <option key={model.filename} value={model.path}>
                                                        {model.filename} - {model.type} {model.variant} ({model.size_mb} MB)
                                                    </option>
                                                ))}
                                            </>
                                        )}
                                    </select>

                                    {/* ✅ Info e badge do modelo atual */}
                                    {/* ✅ Info e badge do modelo atual */}
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-gray-500">
                                            {Array.isArray(yoloModels) && yoloModels.length > 0
                                                ? `${yoloModels.length} modelo(s) em /yolo_models/ (.pt ou .engine)`
                                                : 'Coloque os arquivos .pt ou .engine na pasta /yolo_models/'}
                                        </span>
                                        {formData.model_path && formData.model_path === currentModel && (
                                            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full font-medium">
                                                ✓ Atual
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <SettingsInput
                                    label="Confidence Threshold"
                                    name="conf_thresh"
                                    type="number"
                                    value={formData.conf_thresh || 0}
                                    onChange={handleInputChange}
                                    min={0}
                                    max={1}
                                    step={0.01}
                                    help="Valores entre 0.0 e 1.0"
                                />
                                <SettingsInput
                                    label="Largura de Processamento"
                                    name="target_width"
                                    type="number"
                                    value={formData.target_width || 0}
                                    onChange={handleInputChange}
                                    help="Largura de processamento (ex: 640, 960, 1280)"
                                />
                                <SettingsInput
                                    label="Frame Step"
                                    name="frame_step"
                                    type="number"
                                    value={formData.frame_step || 0}
                                    onChange={handleInputChange}
                                    min={1}
                                    help="Processar 1 a cada N frames"
                                />
                                <SettingsInput
                                    label="Tracker"
                                    name="tracker"
                                    type="select"
                                    value={formData.tracker || ''}
                                    onChange={handleInputChange}
                                    options={[
                                        { value: 'botsort.yaml', label: 'BoT-SORT' },
                                        { value: 'bytetrack.yaml', label: 'ByteTrack' },
                                    ]}
                                    help="Algoritmo de rastreamento"
                                />
                                <SettingsInput
                                    label="Fonte de Vídeo"
                                    name="source"
                                    type="text"
                                    value={formData.source || ''}
                                    onChange={handleInputChange}
                                    help="Webcam (0, 1) ou URL RTSP/HTTP"
                                />
                                <SettingsInput
                                    label="Largura da Câmera"
                                    name="cam_width"
                                    type="number"
                                    value={formData.cam_width || 0}
                                    onChange={handleInputChange}
                                />
                                <SettingsInput
                                    label="Altura da Câmera"
                                    name="cam_height"
                                    type="number"
                                    value={formData.cam_height || 0}
                                    onChange={handleInputChange}
                                />
                                <SettingsInput
                                    label="FPS da Câmera"
                                    name="cam_fps"
                                    type="number"
                                    value={formData.cam_fps || 0}
                                    onChange={handleInputChange}
                                />
                            </div>
                        )}

                        {/* Zones Tab */}
                        {activeTab === 'zones' && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <SettingsInput
                                    label="Tempo Máximo Fora (segundos)"
                                    name="max_out_time"
                                    type="number"
                                    value={formData.max_out_time || 0}
                                    onChange={handleInputChange}
                                    help="Tempo máximo fora da zona antes de alerta"
                                />
                                <SettingsInput
                                    label="Cooldown de Email (segundos)"
                                    name="email_cooldown"
                                    type="number"
                                    value={formData.email_cooldown || 0}
                                    onChange={handleInputChange}
                                    help="Intervalo mínimo entre emails"
                                />
                                <SettingsInput
                                    label="Timeout Zona Vazia (segundos)"
                                    name="zone_empty_timeout"
                                    type="number"
                                    value={formData.zone_empty_timeout || 0}
                                    onChange={handleInputChange}
                                    help="Tempo até considerar zona vazia"
                                />
                                <SettingsInput
                                    label="Timeout Zona Cheia (segundos)"
                                    name="zone_full_timeout"
                                    type="number"
                                    value={formData.zone_full_timeout || 0}
                                    onChange={handleInputChange}
                                    help="Tempo até considerar zona cheia"
                                />
                                <SettingsInput
                                    label="Limite Zona Cheia"
                                    name="zone_full_threshold"
                                    type="number"
                                    value={formData.zone_full_threshold || 0}
                                    onChange={handleInputChange}
                                    help="Número de pessoas para zona cheia"
                                />
                                <SettingsInput
                                    label="Buffer de Vídeo (segundos)"
                                    name="buffer_seconds"
                                    type="number"
                                    value={formData.buffer_seconds || 0}
                                    onChange={handleInputChange}
                                    step={0.1}
                                    help="Buffer de vídeo em segundos"
                                />
                            </div>
                        )}

                        {/* Email Tab */}
                        {activeTab === 'email' && (
                            <div className="space-y-6">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <SettingsInput
                                        label="Servidor SMTP"
                                        name="email_smtp_server"
                                        type="text"
                                        value={formData.email_smtp_server || ''}
                                        onChange={handleInputChange}
                                        help="Endereço do servidor SMTP"
                                    />
                                    <SettingsInput
                                        label="Porta SMTP"
                                        name="email_smtp_port"
                                        type="number"
                                        value={formData.email_smtp_port || 0}
                                        onChange={handleInputChange}
                                    />
                                    <SettingsInput
                                        label="Email Remetente"
                                        name="email_from"
                                        type="text"
                                        value={formData.email_from || ''}
                                        onChange={handleInputChange}
                                        help="Email que aparecerá como remetente"
                                    />
                                    <SettingsInput
                                        label="Usuário SMTP"
                                        name="email_user"
                                        type="text"
                                        value={formData.email_user || ''}
                                        onChange={handleInputChange}
                                        help="Usuário para autenticação SMTP"
                                    />
                                    <div className="md:col-span-2">
                                        <SettingsInput
                                            label="Senha SMTP"
                                            name="email_password"
                                            type="password"
                                            value={formData.email_password || ''}
                                            onChange={handleInputChange}
                                            help="Para Gmail, use App Password (não a senha normal)"
                                        />
                                    </div>
                                </div>

                                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                                    <p className="text-sm text-yellow-800">
                                        <strong>⚠️ Gmail:</strong> Ative verificação em 2 etapas e gere uma "Senha de App" em{' '}
                                        <a
                                            href="https://myaccount.google.com/apppasswords"
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="underline hover:text-yellow-900"
                                        >
                                            myaccount.google.com/apppasswords
                                        </a>
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* System Tab */}
                        {activeTab === 'system' && (
                            <div className="space-y-4">
                                <label className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.use_cuda || false}
                                        onChange={(e) => handleInputChange('use_cuda', e.target.checked)}
                                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                                    />
                                    <div>
                                        <div className="font-medium text-gray-900">Usar GPU (CUDA)</div>
                                        <div className="text-sm text-gray-500">Acelera processamento YOLO usando GPU NVIDIA</div>
                                    </div>
                                </label>

                                <label className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.verbose_logs || false}
                                        onChange={(e) => handleInputChange('verbose_logs', e.target.checked)}
                                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                                    />
                                    <div>
                                        <div className="font-medium text-gray-900">Logs Detalhados</div>
                                        <div className="text-sm text-gray-500">Registra informações de debug no console</div>
                                    </div>
                                </label>

                                <label className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={formData.auto_restart || false}
                                        onChange={(e) => handleInputChange('auto_restart', e.target.checked)}
                                        className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                                    />
                                    <div>
                                        <div className="font-medium text-gray-900">Auto-restart em Erro</div>
                                        <div className="text-sm text-gray-500">Reinicia automaticamente em caso de falha</div>
                                    </div>
                                </label>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </MainLayout>
    );
}
