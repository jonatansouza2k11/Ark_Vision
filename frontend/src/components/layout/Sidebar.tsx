// src/components/layout/Sidebar.tsx
import { NavLink, useNavigate } from 'react-router-dom';
import {
    LayoutDashboard,
    Settings,
    FileText,
    Users,
    LogOut,
    Video,
    //Shield
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

export default function Sidebar() {
    const { user, logout } = useAuthStore();
    const navigate = useNavigate();

    const navigation = [
        { name: 'Dashboard', href: '/', icon: LayoutDashboard },
        { name: 'Configurações', href: '/settings', icon: Settings },
        { name: 'Logs', href: '/logs', icon: FileText },
        ...(user?.role === 'admin' ? [{ name: 'Usuários', href: '/users', icon: Users }] : []),
    ];

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <aside className="flex flex-col h-screen w-64 bg-gray-900 text-white border-r border-gray-800">
            {/* Logo & Brand */}
            <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-800">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg flex items-center justify-center shadow-lg">
                    <Video className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-lg font-bold">ARK YOLO</h1>
                    <p className="text-xs text-gray-400">FastAPI + React</p>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
                {navigation.map((item) => (
                    <NavLink
                        key={item.name}
                        to={item.href}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${isActive
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/50'
                                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                            }`
                        }
                    >
                        <item.icon className="w-5 h-5 flex-shrink-0" />
                        <span className="font-medium">{item.name}</span>
                    </NavLink>
                ))}
            </nav>

            {/* User Info & Logout */}
            <div className="px-3 py-4 border-t border-gray-800 space-y-2">
                {/* User Card */}
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-800">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center font-bold text-sm shadow-md">
                        {user?.username?.charAt(0).toUpperCase() || 'U'}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold truncate">{user?.username}</p>
                        <p className="text-xs text-gray-400 uppercase">{user?.role}</p>
                    </div>
                </div>

                {/* Logout Button */}
                <button
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-4 py-2.5 w-full rounded-lg text-gray-300 hover:bg-red-600 hover:text-white transition-colors"
                >
                    <LogOut className="w-5 h-5" />
                    <span className="font-medium">Sair</span>
                </button>
            </div>
        </aside>
    );
}
