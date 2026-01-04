// src/pages/Logs.tsx
import { useState, useEffect } from 'react';
import { FileText, Download, Trash2, Filter, Calendar, Search } from 'lucide-react';
import MainLayout from '../components/layout/MainLayout';
import { SystemLog } from '../types/dashboard';

export default function Logs() {
    const [logs, setLogs] = useState<SystemLog[]>([]);
    const [filteredLogs, setFilteredLogs] = useState<SystemLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterAction, setFilterAction] = useState<'all' | 'INICIAR' | 'PAUSAR' | 'PARAR' | 'RETOMAR'>('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [dateFilter, setDateFilter] = useState('');

    // Mock data - substituir por chamada API real
    useEffect(() => {
        // TODO: Buscar logs da API
        const mockLogs: SystemLog[] = [
            {
                id: 1,
                action: 'INICIAR',
                username: 'admin',
                reason: 'Início do turno matutino',
                timestamp: '2026-01-02 08:00:15',
                email_sent: false,
            },
            {
                id: 2,
                action: 'PAUSAR',
                username: 'admin',
                reason: 'Manutenção preventiva do sistema',
                timestamp: '2026-01-02 10:30:22',
                email_sent: false,
            },
            {
                id: 3,
                action: 'RETOMAR',
                username: 'operador1',
                reason: 'Manutenção concluída com sucesso',
                timestamp: '2026-01-02 11:15:08',
                email_sent: false,
            },
            {
                id: 4,
                action: 'PAUSAR',
                username: 'admin',
                reason: 'Intervalo de almoço',
                timestamp: '2026-01-02 12:00:00',
                email_sent: false,
            },
            {
                id: 5,
                action: 'RETOMAR',
                username: 'admin',
                reason: 'Retorno do almoço',
                timestamp: '2026-01-02 13:00:00',
                email_sent: false,
            },
            {
                id: 6,
                action: 'PARAR',
                username: 'admin',
                reason: 'Fim do expediente',
                timestamp: '2026-01-02 18:00:00',
                email_sent: true,
            },
        ];

        setLogs(mockLogs);
        setFilteredLogs(mockLogs);
        setLoading(false);
    }, []);

    // Aplicar filtros
    useEffect(() => {
        let filtered = logs;

        // Filtro por ação
        if (filterAction !== 'all') {
            filtered = filtered.filter((log) => log.action === filterAction);
        }

        // Filtro por busca
        if (searchTerm) {
            filtered = filtered.filter(
                (log) =>
                    log.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    log.reason?.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        // Filtro por data
        if (dateFilter) {
            filtered = filtered.filter((log) => log.timestamp.startsWith(dateFilter));
        }

        setFilteredLogs(filtered);
    }, [filterAction, searchTerm, dateFilter, logs]);

    const getActionColor = (action: string) => {
        switch (action) {
            case 'INICIAR':
                return 'bg-green-100 text-green-700 border-green-200';
            case 'PAUSAR':
                return 'bg-yellow-100 text-yellow-700 border-yellow-200';
            case 'RETOMAR':
                return 'bg-blue-100 text-blue-700 border-blue-200';
            case 'PARAR':
                return 'bg-red-100 text-red-700 border-red-200';
            default:
                return 'bg-gray-100 text-gray-700 border-gray-200';
        }
    };

    const handleExportCSV = () => {
        // TODO: Implementar export CSV
        console.log('Exportando CSV...');
    };

    const handleClearLogs = () => {
        if (confirm('Tem certeza que deseja limpar todos os logs?')) {
            // TODO: Implementar limpeza de logs
            console.log('Limpando logs...');
        }
    };

    return (
        <MainLayout>
            <div className="space-y-6 animate-fadeIn">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <FileText className="w-8 h-8 text-blue-600" />
                        <div>
                            <h1 className="text-3xl font-bold text-gray-900">Logs do Sistema</h1>
                            <p className="text-gray-600 mt-1">Histórico de ações e eventos</p>
                        </div>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={handleExportCSV}
                            className="flex items-center gap-2 px-4 py-2 text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
                        >
                            <Download className="w-4 h-4" />
                            <span className="hidden sm:inline">Exportar CSV</span>
                        </button>
                        <button
                            onClick={handleClearLogs}
                            className="flex items-center gap-2 px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                        >
                            <Trash2 className="w-4 h-4" />
                            <span className="hidden sm:inline">Limpar</span>
                        </button>
                    </div>
                </div>

                {/* Filters */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 space-y-4">
                    <div className="flex items-center gap-2">
                        <Filter className="w-5 h-5 text-gray-400" />
                        <h3 className="font-medium text-gray-900">Filtros</h3>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {/* Search */}
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Buscar por usuário ou motivo..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full pl-10 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                            />
                        </div>

                        {/* Action Filter */}
                        <div className="flex gap-2">
                            {['all', 'INICIAR', 'PAUSAR', 'RETOMAR', 'PARAR'].map((action) => (
                                <button
                                    key={action}
                                    onClick={() => setFilterAction(action as any)}
                                    className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors ${filterAction === action
                                        ? 'bg-blue-100 text-blue-700 shadow-sm'
                                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                        }`}
                                >
                                    {action === 'all' ? 'Todos' : action}
                                </button>
                            ))}
                        </div>

                        {/* Date Filter */}
                        <div className="relative">
                            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="date"
                                value={dateFilter}
                                onChange={(e) => setDateFilter(e.target.value)}
                                className="w-full pl-10 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                            />
                        </div>
                    </div>

                    {/* Results count */}
                    <div className="text-sm text-gray-600 pt-2 border-t">
                        Mostrando <span className="font-semibold">{filteredLogs.length}</span> de{' '}
                        <span className="font-semibold">{logs.length}</span> logs
                    </div>
                </div>

                {/* Logs Table */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                    {loading ? (
                        <div className="p-12 text-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="mt-4 text-gray-600">Carregando logs...</p>
                        </div>
                    ) : filteredLogs.length === 0 ? (
                        <div className="p-12 text-center">
                            <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <p className="text-gray-600">Nenhum log encontrado</p>
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-50">
                                    <tr>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            ID
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Data/Hora
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Ação
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Usuário
                                        </th>
                                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Motivo
                                        </th>
                                        <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                                            Email
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {filteredLogs.map((log) => (
                                        <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                                #{log.id}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {log.timestamp}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <span
                                                    className={`px-3 py-1 text-xs font-medium rounded-full border ${getActionColor(
                                                        log.action
                                                    )}`}
                                                >
                                                    {log.action}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold text-xs">
                                                        {log.username.charAt(0).toUpperCase()}
                                                    </div>
                                                    <span className="text-sm font-medium text-gray-900">
                                                        {log.username}
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 text-sm text-gray-600 max-w-md truncate">
                                                {log.reason || '-'}
                                            </td>
                                            <td className="px-6 py-4 whitespace-nowrap text-center">
                                                {log.email_sent ? (
                                                    <span className="inline-flex items-center px-2 py-1 text-xs font-medium text-green-700 bg-green-100 rounded-full">
                                                        ✓ Enviado
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-gray-400">-</span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </MainLayout>
    );
}
