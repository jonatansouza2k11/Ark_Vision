// frontend/src/pages/Logs.tsx

import { useState, useEffect } from 'react';
import { FileText, Download, Trash2, Filter, Calendar, Search, RefreshCw, AlertTriangle } from 'lucide-react';
import MainLayout from '../components/layout/MainLayout';
import { SystemLog } from '../types/logs';
import logsApi from '../services/logsApi';
import { useToast } from '../hooks/useToast';

export default function Logs() {
    const [logs, setLogs] = useState<SystemLog[]>([]);
    const [filteredLogs, setFilteredLogs] = useState<SystemLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const toast = useToast();

    // Filters
    const [filterAction, setFilterAction] = useState<'all' | 'INICIAR' | 'PAUSAR' | 'PARAR' | 'RETOMAR'>('all');
    const [searchTerm, setSearchTerm] = useState('');
    const [dateFilter, setDateFilter] = useState('');

    // Statistics
    const [stats, setStats] = useState({
        total: 0,
        today: 0,
        this_week: 0,
        this_month: 0,
    });

    // ==================== FETCH LOGS ====================
    const fetchLogs = async () => {
        try {
            setLoading(true);
            const response = await logsApi.getSystemLogs(500);
            const fetchedLogs = response.data.logs;
            setLogs(fetchedLogs);
            setFilteredLogs(fetchedLogs);

            // Calculate statistics
            const calculatedStats = logsApi.calculateStatistics(fetchedLogs);
            setStats({
                total: calculatedStats.total,
                today: calculatedStats.today,
                this_week: calculatedStats.this_week,
                this_month: calculatedStats.this_month,
            });

            console.log('✅ [LOGS] Fetched', fetchedLogs.length, 'logs');
        } catch (error: any) {
            console.error('❌ [LOGS] Error fetching logs:', error);
            toast.error('Erro ao carregar logs: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
    }, []);

    // ==================== APPLY FILTERS ====================
    useEffect(() => {
        let filtered = logs;

        // Filter by action
        if (filterAction !== 'all') {
            filtered = filtered.filter((log) => log.action === filterAction);
        }

        // Filter by search term
        if (searchTerm) {
            filtered = filtered.filter(
                (log) =>
                    log.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    log.reason?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    log.action?.toLowerCase().includes(searchTerm.toLowerCase())
            );
        }

        // Filter by date
        if (dateFilter) {
            filtered = filtered.filter((log) => log.timestamp.startsWith(dateFilter));
        }

        setFilteredLogs(filtered);
    }, [filterAction, searchTerm, dateFilter, logs]);

    // ==================== REFRESH ====================
    const handleRefresh = async () => {
        setRefreshing(true);
        await fetchLogs();
        setRefreshing(false);
        toast.success('Logs atualizados!');
    };

    // ==================== EXPORT CSV ====================
    const handleExportCSV = async () => {
        try {
            toast.info('Exportando logs...');
            const response = await logsApi.exportLogs('csv', 1000);

            const blob = new Blob([response.data], { type: 'text/csv' });
            const filename = `logs_${new Date().toISOString().split('T')[0]}.csv`;
            logsApi.downloadBlob(blob, filename);

            toast.success('Logs exportados com sucesso!');
        } catch (error: any) {
            console.error('❌ [LOGS] Export failed:', error);
            toast.error('Erro ao exportar logs: ' + (error.response?.data?.detail || error.message));
        }
    };

    // ==================== EXPORT JSON ====================
    const handleExportJSON = async () => {
        try {
            toast.info('Exportando logs...');
            const response = await logsApi.exportLogs('json', 1000);

            const jsonStr = JSON.stringify(response.data, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const filename = `logs_${new Date().toISOString().split('T')[0]}.json`;
            logsApi.downloadBlob(blob, filename);

            toast.success('Logs exportados com sucesso!');
        } catch (error: any) {
            console.error('❌ [LOGS] Export failed:', error);
            toast.error('Erro ao exportar logs: ' + (error.response?.data?.detail || error.message));
        }
    };

    // ==================== CLEAR OLD LOGS ====================
    const handleClearLogs = async () => {
        if (!confirm('Tem certeza que deseja limpar logs com mais de 30 dias?')) {
            return;
        }

        try {
            toast.info('Limpando logs antigos...');
            await logsApi.clearOldLogs(30);
            toast.success('Logs antigos removidos!');
            await fetchLogs();
        } catch (error: any) {
            console.error('❌ [LOGS] Clear failed:', error);
            toast.error('Erro ao limpar logs: ' + (error.response?.data?.detail || error.message));
        }
    };

    // ==================== GET ACTION COLOR ====================
    const getActionColor = (action: string) => {
        switch (action) {
            case 'INICIAR':
            case 'login':
            case 'user_created':
                return 'bg-green-100 text-green-700 border-green-200';
            case 'PAUSAR':
            case 'settings_changed':
                return 'bg-yellow-100 text-yellow-700 border-yellow-200';
            case 'RETOMAR':
            case 'backup_created':
                return 'bg-blue-100 text-blue-700 border-blue-200';
            case 'PARAR':
            case 'logout':
            case 'user_deleted':
                return 'bg-red-100 text-red-700 border-red-200';
            default:
                return 'bg-gray-100 text-gray-700 border-gray-200';
        }
    };

    // ==================== RENDER ====================
    return (
        <MainLayout>
            <div className="space-y-6 animate-fadeIn">
                {/* ==================== HEADER ==================== */}
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
                            onClick={handleRefresh}
                            disabled={refreshing}
                            className="flex items-center gap-2 px-4 py-2 text-gray-700 bg-white hover:bg-gray-50 border border-gray-300 rounded-lg transition-colors disabled:opacity-50"
                        >
                            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                            <span className="hidden sm:inline">Atualizar</span>
                        </button>

                        {/* Export Dropdown */}
                        <div className="relative group">
                            <button className="flex items-center gap-2 px-4 py-2 text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors">
                                <Download className="w-4 h-4" />
                                <span className="hidden sm:inline">Exportar</span>
                            </button>
                            <div className="absolute right-0 mt-2 w-40 bg-white border border-gray-200 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
                                <button
                                    onClick={handleExportCSV}
                                    className="w-full text-left px-4 py-2 hover:bg-gray-50 rounded-t-lg"
                                >
                                    Exportar CSV
                                </button>
                                <button
                                    onClick={handleExportJSON}
                                    className="w-full text-left px-4 py-2 hover:bg-gray-50 rounded-b-lg"
                                >
                                    Exportar JSON
                                </button>
                            </div>
                        </div>

                        <button
                            onClick={handleClearLogs}
                            className="flex items-center gap-2 px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                        >
                            <Trash2 className="w-4 h-4" />
                            <span className="hidden sm:inline">Limpar</span>
                        </button>
                    </div>
                </div>

                {/* ==================== STATISTICS ==================== */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                        <p className="text-gray-600 text-sm mb-1">Total de Logs</p>
                        <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                        <p className="text-gray-600 text-sm mb-1">Hoje</p>
                        <p className="text-2xl font-bold text-blue-600">{stats.today}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                        <p className="text-gray-600 text-sm mb-1">Esta Semana</p>
                        <p className="text-2xl font-bold text-green-600">{stats.this_week}</p>
                    </div>
                    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                        <p className="text-gray-600 text-sm mb-1">Este Mês</p>
                        <p className="text-2xl font-bold text-purple-600">{stats.this_month}</p>
                    </div>
                </div>

                {/* ==================== FILTERS ==================== */}
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
                                placeholder="Buscar por usuário, motivo ou ação..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="w-full pl-10 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
                            />
                        </div>

                        {/* Action Filter */}
                        <div className="flex gap-2 overflow-x-auto">
                            {['all', 'INICIAR', 'PAUSAR', 'RETOMAR', 'PARAR'].map((action) => (
                                <button
                                    key={action}
                                    onClick={() => setFilterAction(action as any)}
                                    className={`px-3 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${filterAction === action
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

                {/* ==================== LOGS TABLE ==================== */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                    {loading ? (
                        <div className="p-12 text-center">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="mt-4 text-gray-600">Carregando logs...</p>
                        </div>
                    ) : filteredLogs.length === 0 ? (
                        <div className="p-12 text-center">
                            <AlertTriangle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <p className="text-gray-600">Nenhum log encontrado</p>
                            <p className="text-sm text-gray-500 mt-2">Tente ajustar os filtros</p>
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
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">#{log.id}</td>
                                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                                {new Date(log.timestamp).toLocaleString('pt-BR')}
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
                                                        {log.username?.charAt(0).toUpperCase() || '?'}
                                                    </div>
                                                    <span className="text-sm font-medium text-gray-900">{log.username || 'N/A'}</span>
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
