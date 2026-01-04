// src/components/dashboard/ZoneModesInfo.tsx
import { AlertCircle, TrendingUp, ShieldAlert, Activity } from 'lucide-react';

const zoneModes = [
    {
        mode: 'FLOW',
        title: 'FLOW (Fluxo)',
        icon: TrendingUp,
        color: 'bg-blue-500',
        description:
            'Zona onde deve haver movimento contínuo (corredor, entrada, esteira, faixa de pedestre industrial). Interessa detectar quando fica vazia por muito tempo ou quando o fluxo reduz demais.',
    },
    {
        mode: 'QUEUE',
        title: 'QUEUE (Fila / Gargalo / Tráfego)',
        icon: Activity,
        color: 'bg-yellow-500',
        description:
            'Zona onde filas são esperadas, mas não devem passar de certo tamanho/tempo (checkout, portaria, guichê). Foco em ocupação alta por tempo demais (fila longa persistente).',
    },
    {
        mode: 'CRITICAL',
        title: 'CRITICAL (Zona de risco)',
        icon: ShieldAlert,
        color: 'bg-red-500',
        description:
            'Área onde a simples presença já é problema (proximidade de máquinas, áreas de risco). Entrada não autorizada, muitas pessoas ou permanência longa disparam alertas.',
    },
    {
        mode: 'GENERIC',
        title: 'GENERIC (Genérico)',
        icon: AlertCircle,
        color: 'bg-gray-500',
        description:
            'Monitoramento geral de ocupação e uso de espaço (loja, sala, estacionamento, ambiente doméstico). Usa checks básicos de ocupado/vazio e tempo.',
    },
];

export default function ZoneModesInfo() {
    return (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Modos de Zona</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {zoneModes.map((zone) => {
                    const Icon = zone.icon;
                    return (
                        <div
                            key={zone.mode}
                            className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                        >
                            <div className="flex items-start gap-3 mb-3">
                                <div className={`p-2 rounded-lg ${zone.color}`}>
                                    <Icon className="w-5 h-5 text-white" />
                                </div>
                                <div className="flex-1">
                                    <h3 className="font-semibold text-gray-900">{zone.title}</h3>
                                </div>
                            </div>
                            <p className="text-sm text-gray-600 leading-relaxed">
                                {zone.description}
                            </p>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
