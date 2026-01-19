// src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';

// Pages
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Users from './pages/Users';
import Settings from './pages/Settings';
import Logs from './pages/Logs';
import Cameras from './pages/Cameras';
import NotFound from './pages/NotFound';

// Components
import ProtectedRoute from './components/ProtectedRoute';
import ZonesManager from './components/zones/ZonesManager';
import StreamViewer from './components/stream/StreamViewer';  // 🔥 NOVO

// Context & Store
import { useAuthStore } from './store/authStore';
import { usersApi } from './api/users';
import { ToastProvider } from './contexts/ToastContext';
import ToastContainer from './components/ToastContainer';

function App() {
  const { user, token, login } = useAuthStore();
  const [loading, setLoading] = useState(true);

  // Carregar usuário ao iniciar app
  useEffect(() => {
    const loadUser = async () => {
      if (token && !user) {
        try {
          const userData = await usersApi.getMe();
          login(userData, token);
        } catch (error) {
          console.error('Erro ao carregar usuário:', error);
          useAuthStore.getState().logout();
        }
      }
      setLoading(false);
    };

    loadUser();
  }, [token, user, login]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          {/* ============================================ */}
          {/* PUBLIC ROUTES */}
          {/* ============================================ */}
          <Route
            path="/login"
            element={token ? <Navigate to="/" replace /> : <Login />}
          />

          {/* ============================================ */}
          {/* PROTECTED ROUTES */}
          {/* ============================================ */}

          {/* Dashboard */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Users (ADMIN only) */}
          <Route
            path="/users"
            element={
              <ProtectedRoute adminOnly>
                <Users />
              </ProtectedRoute>
            }
          />

          {/* Cameras Management */}
          <Route
            path="/cameras"
            element={
              <ProtectedRoute>
                <Cameras />
              </ProtectedRoute>
            }
          />

          {/* Zones Management */}
          <Route
            path="/zones"
            element={
              <ProtectedRoute>
                <ZonesManager />
              </ProtectedRoute>
            }
          />

          {/* 🔥 NOVO: Stream Viewer */}
          <Route
            path="/stream"
            element={
              <ProtectedRoute>
                <StreamViewer />
              </ProtectedRoute>
            }
          />

          {/* Settings */}
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            }
          />

          {/* Logs */}
          <Route
            path="/logs"
            element={
              <ProtectedRoute>
                <Logs />
              </ProtectedRoute>
            }
          />

          {/* ============================================ */}
          {/* 404 NOT FOUND */}
          {/* ============================================ */}
          <Route path="*" element={<NotFound />} />
        </Routes>

        {/* Toast Notifications */}
        <ToastContainer />
      </BrowserRouter>
    </ToastProvider>
  );
}

export default App;
