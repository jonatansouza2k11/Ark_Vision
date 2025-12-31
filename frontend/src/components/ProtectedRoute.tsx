// src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

interface ProtectedRouteProps {
    children: React.ReactNode;
    adminOnly?: boolean;
}

export default function ProtectedRoute({ children, adminOnly = false }: ProtectedRouteProps) {
    const { user, token } = useAuthStore();

    // Sem token = não autenticado
    if (!token) {
        return <Navigate to="/login" replace />;
    }

    // Admin only e usuário não é admin
    if (adminOnly && user?.role !== 'admin') {
        return <Navigate to="/" replace />;
    }

    return <>{children}</>;
}
