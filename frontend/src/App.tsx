import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Customers from './pages/erp/Customers';
import Contracts from './pages/erp/Contracts';
import Report from './pages/Report';
import Settings from './pages/Settings';
import UserManagement from './pages/UserManagement';
import Login from './pages/Login';
import { useAuth } from './contexts/AuthContext';
import type { UserRole } from './types';

const RequireAuth: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { loading, isAuthenticated } = useAuth();
  if (loading) {
    return <div className="h-screen flex items-center justify-center text-gray-600">인증 확인 중...</div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

const RequireRole: React.FC<{ role: UserRole; children: React.ReactElement }> = ({ role, children }) => {
  const { hasRole } = useAuth();
  if (!hasRole(role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <MainLayout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="customers" element={<Customers />} />
          <Route path="contracts" element={<Contracts />} />
          <Route path="report" element={<Report />} />
          <Route
            path="settings"
            element={
              <RequireRole role="SYSTEM_ADMIN">
                <Settings />
              </RequireRole>
            }
          />
          <Route
            path="user-management"
            element={
              <RequireRole role="SYSTEM_ADMIN">
                <UserManagement />
              </RequireRole>
            }
          />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
