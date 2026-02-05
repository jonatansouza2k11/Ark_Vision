/**
 * CameraForm.tsx - Camera Create/Edit Form
 * Form component for creating and editing cameras
 */

import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { toast } from 'sonner';
import type { Camera, CameraFormData } from '../../types/cameras.types';
import { TRACKER_OPTIONS, type TrackerType } from '../../types/trackers.types';

import { DEFAULT_CAMERA_FORM, validateCameraForm } from '../../types/cameras.types';

// ============================================
// TYPES
// ============================================

interface CameraFormProps {
    camera?: Camera | null;
    onSubmit: (data: CameraFormData) => Promise<void>;
    onCancel: () => void;
    isOpen: boolean;
}

// ============================================
// COMPONENT
// ============================================

export function CameraForm({ camera, onSubmit, onCancel, isOpen }: CameraFormProps) {
    const [formData, setFormData] = useState<CameraFormData>(DEFAULT_CAMERA_FORM);
    const [errors, setErrors] = useState<string[]>([]);
    const [submitting, setSubmitting] = useState(false);

    const isEditMode = !!camera;

    // ============================================
    // EFFECTS
    // ============================================

    useEffect(() => {
        if (camera) {
            setFormData({
                name: camera.name,
                source: camera.source,
                location: camera.location || '',
                username: camera.username || '',
                password: '', // Never prefill password
                enabled: camera.enabled,
                metadata: camera.metadata || {}
            });
        } else {
            setFormData(DEFAULT_CAMERA_FORM);
        }
        setErrors([]);
    }, [camera, isOpen]);

    // ============================================
    // HANDLERS
    // ============================================

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value, type } = e.target;
        const checked = (e.target as HTMLInputElement).checked;

        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate
        const validationErrors = validateCameraForm(formData);
        if (validationErrors.length > 0) {
            setErrors(validationErrors);
            validationErrors.forEach(error => toast.error(error));
            return;
        }

        setSubmitting(true);
        setErrors([]);

        try {
            await onSubmit(formData);
            setFormData(DEFAULT_CAMERA_FORM);
            toast.success(isEditMode ? 'Câmera atualizada com sucesso!' : 'Câmera criada com sucesso!');
        } catch (err: any) {
            const errorMsg = err?.message || 'Erro ao salvar câmera';
            setErrors([errorMsg]);
            toast.error(errorMsg);
        } finally {
            setSubmitting(false);
        }
    };

    // ============================================
    // RENDER
    // ============================================

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b">
                    <h2 className="text-2xl font-bold text-gray-900">
                        {isEditMode ? 'Editar Câmera' : 'Nova Câmera'}
                    </h2>
                    <button
                        onClick={onCancel}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                        disabled={submitting}
                    >
                        <X size={24} />
                    </button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">
                    {/* Errors */}
                    {errors.length > 0 && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                            <ul className="list-disc list-inside text-red-700 text-sm space-y-1">
                                {errors.map((error, index) => (
                                    <li key={index}>{error}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Name */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Nome da Câmera <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            name="name"
                            value={formData.name}
                            onChange={handleChange}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Ex: Câmera Principal"
                            required
                            maxLength={100}
                            disabled={submitting}
                        />
                    </div>

                    {/* Source */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Source (URL/Device) <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            name="source"
                            value={formData.source}
                            onChange={handleChange}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                            placeholder="rtsp://192.168.1.100:554/stream ou 0"
                            required
                            maxLength={500}
                            disabled={submitting}
                        />
                        <p className="mt-1 text-xs text-gray-500">
                            Exemplos: rtsp://ip:port/stream, http://url, 0 (webcam), video.mp4
                        </p>
                    </div>

                    {/* Location */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Localização
                        </label>
                        <input
                            type="text"
                            name="location"
                            value={formData.location}
                            onChange={handleChange}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Ex: Entrada Principal"
                            maxLength={255}
                            disabled={submitting}
                        />
                    </div>

                    {/* Username */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Username (RTSP)
                        </label>
                        <input
                            type="text"
                            name="username"
                            value={formData.username}
                            onChange={handleChange}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="admin"
                            maxLength={100}
                            disabled={submitting}
                            autoComplete="off"
                        />
                    </div>

                    {/* Password */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Password (RTSP)
                        </label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder={isEditMode ? 'Deixe vazio para não alterar' : 'Senha'}
                            maxLength={255}
                            disabled={submitting}
                            autoComplete="new-password"
                        />
                    </div>

                    {/* Default tracker */}
                    <div className="space-y-1">
                        <label className="block text-sm font-medium text-gray-700">
                            Tracker padrão
                        </label>

                        <select
                            value={(formData.metadata.default_tracker ?? '') as string}
                            onChange={e => {
                                const value = e.target.value as TrackerType | '';
                                setFormData(prev => ({
                                    ...prev,
                                    metadata: {
                                        ...(prev.metadata || {}),
                                        default_tracker: value === '' ? undefined : value,
                                    },
                                }));
                            }}
                            className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">
                                Automático (padrão do sistema)
                            </option>
                            {TRACKER_OPTIONS.map(opt => (
                                <option key={opt.value} value={opt.value}>
                                    {opt.label}
                                </option>
                            ))}
                        </select>

                        <p className="text-xs text-gray-500">
                            {formData.metadata.default_tracker
                                ? TRACKER_OPTIONS.find(
                                    o => o.value === formData.metadata.default_tracker
                                )?.description
                                : 'Se não escolher, será usado o tracker padrão global (ex. ByteTrack YOLO).'}
                        </p>
                    </div>

                    {/* Enabled */}
                    <div className="flex items-center space-x-2">
                        <input
                            type="checkbox"
                            name="enabled"
                            checked={formData.enabled}
                            onChange={handleChange}
                            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            disabled={submitting}
                        />
                        <label className="text-sm font-medium text-gray-700">
                            Câmera Ativa
                        </label>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center justify-end space-x-3 pt-4 border-t">
                        <button
                            type="button"
                            onClick={onCancel}
                            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                            disabled={submitting}
                        >
                            Cancelar
                        </button>
                        <button
                            type="submit"
                            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={submitting}
                        >
                            {submitting ? 'Salvando...' : isEditMode ? 'Atualizar' : 'Criar'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default CameraForm;
