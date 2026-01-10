// frontend/src/components/settings/SettingsInput.tsx

/**
 * SettingsInput Component v3.0
 * Reusable input with validation
 */

import React from 'react';

interface SettingsInputProps {
    label: string;
    name: string;
    type: 'text' | 'number' | 'select' | 'password';
    value: string | number;
    onChange: (name: string, value: any) => void;
    options?: { value: string; label: string }[];
    help?: string;
    error?: string;
    min?: number;
    max?: number;
    step?: number;
}

export const SettingsInput: React.FC<SettingsInputProps> = ({
    label,
    name,
    type,
    value,
    onChange,
    options,
    help,
    error,
    min,
    max,
    step,
}) => {
    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const newValue = type === 'number' ? parseFloat(e.target.value) : e.target.value;
        onChange(name, newValue);
    };

    return (
        <div className="space-y-2">
            <label htmlFor={name} className="block text-sm font-medium text-gray-700">
                {label}
            </label>

            {type === 'select' ? (
                <select
                    id={name}
                    name={name}
                    value={value}
                    onChange={handleChange}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${error ? 'border-red-500' : 'border-gray-300'
                        }`}
                >
                    {options?.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                            {opt.label}
                        </option>
                    ))}
                </select>
            ) : (
                <input
                    id={name}
                    name={name}
                    type={type}
                    value={value}
                    onChange={handleChange}
                    min={min}
                    max={max}
                    step={step}
                    className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${error ? 'border-red-500' : 'border-gray-300'
                        }`}
                />
            )}

            {help && !error && (
                <p className="text-xs text-gray-500">{help}</p>
            )}

            {error && (
                <p className="text-xs text-red-600">{error}</p>
            )}
        </div>
    );
};
