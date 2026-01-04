// frontend/src/hooks/useSettings.ts

/**
 * useSettings Hook v4.0
 * Com validação em tempo real
 */

import { useState, useCallback, useEffect } from 'react';
import { settingsApi } from '../api/settingsApi';
import type { AllSettings, YOLOConfig, EmailConfig, FieldValidation } from '../types/settings.types';

interface UseSettingsReturn {
    settings: Partial<AllSettings> | null;
    originalSettings: Partial<AllSettings> | null;
    loading: boolean;
    saving: boolean;
    error: string | null;
    hasChanges: boolean;
    validateField: (field: string, value: any) => FieldValidation;
    updateSettings: (updates: Partial<AllSettings>) => Promise<boolean>;
    updateYoloConfig: (config: Partial<YOLOConfig>) => Promise<boolean>;
    updateEmailConfig: (config: Partial<EmailConfig>) => Promise<boolean>;
    resetSettings: () => Promise<boolean>;
    refetch: () => Promise<void>;
    discardChanges: () => void;
}

export const useSettings = (): UseSettingsReturn => {
    const [settings, setSettings] = useState<Partial<AllSettings> | null>(null);
    const [originalSettings, setOriginalSettings] = useState<Partial<AllSettings> | null>(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const parseSettings = useCallback((raw: Record<string, any>): Partial<AllSettings> => {
        return {
            // YOLO
            model_path: raw.model_path || 'yolov8n.pt',
            conf_thresh: parseFloat(raw.conf_thresh) || 0.87,
            target_width: parseInt(raw.target_width) || 960,
            frame_step: parseInt(raw.frame_step) || 1,
            tracker: raw.tracker || 'BoT-SORT',
            source: raw.source || '0',
            cam_width: parseInt(raw.cam_width) || 1280,
            cam_height: parseInt(raw.cam_height) || 720,
            cam_fps: parseInt(raw.cam_fps) || 30,
            // Zones
            max_out_time: parseFloat(raw.max_out_time) || 20.0,
            email_cooldown: parseFloat(raw.email_cooldown) || 120.0,
            zone_empty_timeout: parseFloat(raw.zone_empty_timeout) || 5.0,
            zone_full_timeout: parseFloat(raw.zone_full_timeout) || 10.0,
            zone_full_threshold: parseInt(raw.zone_full_threshold) || 3,
            buffer_seconds: parseFloat(raw.buffer_seconds) || 2.0,
            // Email
            email_smtp_server: raw.email_smtp_server || 'smtp.gmail.com',
            email_smtp_port: parseInt(raw.email_smtp_port) || 587,
            email_user: raw.email_user || '',
            email_password: raw.email_password || '',
            email_from: raw.email_from || '',
            // System
            use_cuda: raw.use_cuda === 'true' || raw.use_cuda === true,
            verbose_logs: raw.verbose_logs === 'true' || raw.verbose_logs === true,
            auto_restart: raw.auto_restart === 'true' || raw.auto_restart === true,
        };
    }, []);

    // ========== NEW v4.0: Validação em Tempo Real ==========

    const validateField = useCallback((field: string, value: any): FieldValidation => {
        // YOLO validations
        if (field === 'conf_thresh') {
            const val = parseFloat(value);
            if (isNaN(val) || val < 0 || val > 1) {
                return { valid: false, message: 'Deve estar entre 0.0 e 1.0', level: 'error' };
            }
            if (val < 0.3) {
                return { valid: true, message: 'Valor baixo pode gerar muitos falsos positivos', level: 'warning' };
            }
            return { valid: true };
        }

        if (field === 'target_width') {
            const val = parseInt(value);
            if (isNaN(val) || val < 320) {
                return { valid: false, message: 'Mínimo: 320 pixels', level: 'error' };
            }
            if (val > 1920) {
                return { valid: true, message: 'Valor alto pode reduzir performance', level: 'warning' };
            }
            return { valid: true };
        }

        if (field === 'frame_step') {
            const val = parseInt(value);
            if (isNaN(val) || val < 1) {
                return { valid: false, message: 'Mínimo: 1', level: 'error' };
            }
            if (val > 5) {
                return { valid: true, message: 'Valor alto pode perder detecções', level: 'warning' };
            }
            return { valid: true };
        }

        if (field === 'email_smtp_port') {
            const val = parseInt(value);
            if (isNaN(val) || val < 1 || val > 65535) {
                return { valid: false, message: 'Porta inválida (1-65535)', level: 'error' };
            }
            return { valid: true };
        }

        if (field === 'cam_fps') {
            const val = parseInt(value);
            if (isNaN(val) || val < 1) {
                return { valid: false, message: 'FPS inválido', level: 'error' };
            }
            if (val > 60) {
                return { valid: true, message: 'FPS muito alto pode causar problemas', level: 'warning' };
            }
            return { valid: true };
        }

        return { valid: true };
    }, []);

    const fetchSettings = useCallback(async () => {
        setLoading(true);
        setError(null);

        const { data, error: apiError } = await settingsApi.getAll();

        if (apiError) {
            setError(apiError);
            setSettings(null);
            setOriginalSettings(null);
        } else if (data) {
            const parsed = parseSettings(data);
            setSettings(parsed);
            setOriginalSettings(parsed);
        }

        setLoading(false);
    }, [parseSettings]);

    const updateSettings = useCallback(async (updates: Partial<AllSettings>): Promise<boolean> => {
        setSaving(true);
        setError(null);

        const apiFormat: Record<string, any> = {};
        Object.entries(updates).forEach(([key, value]) => {
            if (typeof value === 'boolean') {
                apiFormat[key] = value ? 'true' : 'false';
            } else {
                apiFormat[key] = String(value);
            }
        });

        const { error: apiError } = await settingsApi.updateMultiple(apiFormat);

        if (apiError) {
            setError(apiError);
            setSaving(false);
            return false;
        }

        await fetchSettings();
        setSaving(false);
        return true;
    }, [fetchSettings]);

    const updateYoloConfig = useCallback(async (config: Partial<YOLOConfig>): Promise<boolean> => {
        setSaving(true);
        setError(null);

        const { error: apiError } = await settingsApi.updateYoloConfig(config);

        if (apiError) {
            setError(apiError);
            setSaving(false);
            return false;
        }

        await fetchSettings();
        setSaving(false);
        return true;
    }, [fetchSettings]);

    const updateEmailConfig = useCallback(async (config: Partial<EmailConfig>): Promise<boolean> => {
        setSaving(true);
        setError(null);

        const { error: apiError } = await settingsApi.updateEmailConfig(config);

        if (apiError) {
            setError(apiError);
            setSaving(false);
            return false;
        }

        await fetchSettings();
        setSaving(false);
        return true;
    }, [fetchSettings]);

    const resetSettings = useCallback(async (): Promise<boolean> => {
        setSaving(true);
        setError(null);

        const { error: apiError } = await settingsApi.reset();

        if (apiError) {
            setError(apiError);
            setSaving(false);
            return false;
        }

        await fetchSettings();
        setSaving(false);
        return true;
    }, [fetchSettings]);

    const discardChanges = useCallback(() => {
        if (originalSettings) {
            setSettings({ ...originalSettings });
        }
    }, [originalSettings]);

    const hasChanges = JSON.stringify(settings) !== JSON.stringify(originalSettings);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    return {
        settings,
        originalSettings,
        loading,
        saving,
        error,
        hasChanges,
        validateField,
        updateSettings,
        updateYoloConfig,
        updateEmailConfig,
        resetSettings,
        refetch: fetchSettings,
        discardChanges,
    };
};
